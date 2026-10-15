"""Transaction explorer endpoints."""
from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.audit_event import AuditEvent
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.schemas.common import PaginatedResponse
from app.schemas.transaction import TransactionRead, TransactionList

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TransactionList])
async def list_transactions(
    status: Optional[str] = None,
    recovery_status: Optional[str] = None,
    failure_category: Optional[str] = None,
    transaction_type: Optional[str] = None,
    batch_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TransactionList]:
    query = select(Transaction)

    if status:
        query = query.where(Transaction.status == status)
    if recovery_status:
        query = query.where(Transaction.recovery_status == recovery_status)
    if failure_category:
        query = query.where(Transaction.failure_category == failure_category)
    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type)
    if batch_id:
        query = query.where(Transaction.batch_id == batch_id)
    if search:
        query = query.where(
            or_(
                Transaction.external_id.ilike(f"%{search}%"),
                Transaction.customer_ref.ilike(f"%{search}%"),
                Transaction.id.ilike(f"%{search}%"),
            )
        )

    # Count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    # Page
    offset = (page - 1) * page_size
    query = query.order_by(Transaction.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    transactions = result.scalars().all()

    return PaginatedResponse(
        items=[TransactionList.model_validate(t) for t in transactions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
) -> TransactionRead:
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise NotFoundError("Transaction", transaction_id)
    return TransactionRead.model_validate(txn)


@router.get("/{transaction_id}/audit", response_model=list)
async def get_transaction_audit(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
) -> list:
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.transaction_id == transaction_id)
        .order_by(AuditEvent.created_at.asc())
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "created_at": e.created_at.isoformat(),
            "event_type": e.event_type,
            "previous_state": e.previous_state,
            "new_state": e.new_state,
            "actor": e.actor,
            "policy_decision": e.policy_decision,
            "action_attempted": e.action_attempted,
            "final_outcome": e.final_outcome,
            "error_details": e.error_details,
            "recommendation": e.recommendation,
        }
        for e in events
    ]


@router.get("/{transaction_id}/recovery-case")
async def get_transaction_recovery_case(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RecoveryCase)
        .where(RecoveryCase.transaction_id == transaction_id)
        .options(
            selectinload(RecoveryCase.recommendations),
            selectinload(RecoveryCase.actions),
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise NotFoundError("RecoveryCase", f"for transaction {transaction_id}")

    return {
        "id": case.id,
        "state": case.state,
        "category": case.category,
        "priority": case.priority,
        "at_risk_amount": float(case.at_risk_amount),
        "estimated_recoverable_amount": float(case.estimated_recoverable_amount or 0),
        "recovered_amount": float(case.recovered_amount),
        "currency": case.currency,
        "action_count": case.action_count,
        "requires_human_review": case.requires_human_review,
        "human_review_reason": case.human_review_reason,
        "close_reason": case.close_reason,
        "is_simulated": case.is_simulated,
        "recommendations": [
            {
                "id": r.id,
                "recommended_action": r.recommended_action,
                "reason": r.reason,
                "evidence": r.evidence,
                "confidence": float(r.confidence),
                "expected_recovery_value": float(r.expected_recovery_value or 0),
                "estimated_cost": float(r.estimated_cost or 0),
                "potential_customer_impact": r.potential_customer_impact,
                "requires_human_approval": r.requires_human_approval,
                "source": r.source,
                "status": r.status,
            }
            for r in case.recommendations
        ],
        "actions": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "execution_mode": a.execution_mode,
                "status": a.status,
                "policy_allowed": a.policy_allowed,
                "policy_reason": a.policy_reason,
                "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                "recovered_amount": float(a.recovered_amount or 0),
                "is_duplicate_prevented": a.is_duplicate_prevented,
                "error_details": a.error_details,
            }
            for a in case.actions
        ],
    }


@router.get("/export/csv")
async def export_transactions_csv(
    status: Optional[str] = None,
    recovery_status: Optional[str] = None,
    batch_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Export filtered transactions to CSV with formula injection protection."""
    query = select(Transaction)
    if status:
        query = query.where(Transaction.status == status)
    if recovery_status:
        query = query.where(Transaction.recovery_status == recovery_status)
    if batch_id:
        query = query.where(Transaction.batch_id == batch_id)

    result = await db.execute(query.limit(5000))
    transactions = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "external_id", "merchant_id", "customer_ref", "amount", "currency",
        "transaction_type", "status", "failure_reason", "failure_category",
        "retry_count", "risk_score", "recoverability", "recovery_status",
        "payment_method", "gateway", "created_at",
    ])

    def safe_val(v) -> str:
        """Prevent CSV formula injection."""
        s = str(v) if v is not None else ""
        if s and s[0] in ("=", "+", "-", "@"):
            return "'" + s
        return s

    for t in transactions:
        writer.writerow([
            safe_val(t.id), safe_val(t.external_id), safe_val(t.merchant_id),
            safe_val(t.customer_ref), safe_val(t.amount), safe_val(t.currency),
            safe_val(t.transaction_type), safe_val(t.status),
            safe_val(t.failure_reason), safe_val(t.failure_category),
            safe_val(t.retry_count), safe_val(t.risk_score),
            safe_val(t.recoverability), safe_val(t.recovery_status),
            safe_val(t.payment_method), safe_val(t.gateway),
            safe_val(t.created_at.isoformat() if t.created_at else ""),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )
