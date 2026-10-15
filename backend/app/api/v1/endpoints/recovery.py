"""Recovery agent endpoints — queue, process, approve, reject."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.recovery_agent import RecoveryAgent
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.approval_record import ApprovalRecord
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.recovery_recommendation import RecoveryRecommendation
from app.models.transaction import Transaction
from app.schemas.recovery_case import ApproveActionRequest, RejectActionRequest
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/queue")
async def get_recovery_queue(
    state: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return all active recovery cases with pagination."""
    query = select(RecoveryCase).options(
        selectinload(RecoveryCase.recommendations),
        selectinload(RecoveryCase.actions),
    )

    if state:
        query = query.where(RecoveryCase.state == state.upper())
    else:
        # Default: exclude only CLOSED — show all active including BLOCKED/FAILED/HUMAN_REVIEW
        query = query.where(
            RecoveryCase.state.not_in(["CLOSED"])
        )
    if category:
        query = query.where(RecoveryCase.category == category)
    if priority:
        query = query.where(RecoveryCase.priority == priority)

    # Count
    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(RecoveryCase.created_at.desc()).offset(offset).limit(page_size)
    )
    cases = result.scalars().all()

    return {
        "items": [
            {
                "id": c.id,
                "transaction_id": c.transaction_id,
                "merchant_id": c.merchant_id,
                "customer_ref": c.customer_ref,
                "category": c.category,
                "state": c.state,
                "priority": c.priority,
                "at_risk_amount": float(c.at_risk_amount),
                "estimated_recoverable_amount": float(c.estimated_recoverable_amount or 0),
                "recovered_amount": float(c.recovered_amount),
                "currency": c.currency,
                "action_count": c.action_count,
                "requires_human_review": c.requires_human_review,
                "risk_score": float(c.risk_score) if c.risk_score else None,
                "created_at": c.created_at.isoformat(),
                "latest_recommendation": (
                    c.recommendations[-1].recommended_action
                    if c.recommendations else None
                ),
            }
            for c in cases
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/process/{transaction_id}", status_code=status.HTTP_201_CREATED)
async def process_transaction(
    transaction_id: str,
    auto_execute: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Run the recovery agent on a single transaction."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise NotFoundError("Transaction", transaction_id)

    agent = RecoveryAgent(db=db)
    case = await agent.process_transaction(txn, auto_execute=auto_execute)

    return {
        "case_id": case.id,
        "transaction_id": transaction_id,
        "state": case.state,
        "category": case.category,
        "priority": case.priority,
        "at_risk_amount": float(case.at_risk_amount),
        "recovered_amount": float(case.recovered_amount),
        "requires_human_review": case.requires_human_review,
    }


@router.post("/process-batch")
async def process_batch(
    batch_id: str,
    auto_execute: bool = True,
    max_cases: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Run the recovery agent on all eligible transactions in a batch."""
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.batch_id == batch_id,
            Transaction.status.in_(["failed", "abandoned", "overdue"]),
            # Process ALL unresolved cases including those needing policy enforcement
            Transaction.recovery_status.not_in(["recovered", "closed"]),
        )
        .limit(max_cases)
    )
    transactions = list(result.scalars().all())

    if not transactions:
        return {"processed": 0, "message": "No eligible transactions found"}

    agent_run_id = str(uuid.uuid4())
    batch_action_count = 0
    outcomes = {"succeeded": 0, "failed": 0, "blocked": 0, "human_review": 0, "other": 0}

    for txn in transactions:
        agent = RecoveryAgent(
            db=db,
            agent_run_id=agent_run_id,
            batch_action_count=batch_action_count,
        )
        try:
            case = await agent.process_transaction(
                txn, auto_execute=auto_execute, batch_id=batch_id
            )
            batch_action_count = agent.batch_action_count
            state = case.state.lower()
            if state in outcomes:
                outcomes[state] += 1
            else:
                outcomes["other"] += 1
        except Exception as exc:
            outcomes["other"] += 1

    return {
        "batch_id": batch_id,
        "agent_run_id": agent_run_id,
        "processed": len(transactions),
        "outcomes": outcomes,
        "batch_action_count": batch_action_count,
    }


@router.post("/{case_id}/approve")
async def approve_action(
    case_id: str,
    request: ApproveActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending recommendation and execute the action."""
    case_result = await db.execute(
        select(RecoveryCase)
        .where(RecoveryCase.id == case_id)
        .options(selectinload(RecoveryCase.recommendations))
    )
    case = case_result.scalar_one_or_none()
    if not case:
        raise NotFoundError("RecoveryCase", case_id)

    rec_result = await db.execute(
        select(RecoveryRecommendation)
        .where(
            RecoveryRecommendation.id == request.recommendation_id,
            RecoveryRecommendation.recovery_case_id == case_id,
        )
    )
    rec = rec_result.scalar_one_or_none()
    if not rec:
        raise NotFoundError("RecoveryRecommendation", request.recommendation_id)

    # Create approval record
    approval = ApprovalRecord(
        recovery_case_id=case_id,
        recommendation_id=rec.id,
        status="approved",
        approver_id=request.approver_id,
        approver_note=request.note,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(approval)

    # Transition to APPROVED
    case.state = "APPROVED"
    db.add(case)
    await db.flush()

    # Load transaction and execute
    txn_result = await db.execute(
        select(Transaction).where(Transaction.id == case.transaction_id)
    )
    txn = txn_result.scalar_one_or_none()
    if txn:
        agent = RecoveryAgent(db=db)
        await agent._execute_action(case, txn, rec)

    audit = AuditService(db)
    await audit.record(
        "APPROVED",
        transaction_id=case.transaction_id,
        recovery_case_id=case_id,
        actor=request.approver_id or "system_user",
        approval_details={"approver": request.approver_id, "note": request.note},
        previous_state="APPROVAL_REQUIRED",
        new_state=case.state,
    )

    return {"status": "approved", "case_id": case_id, "new_state": case.state}


@router.post("/{case_id}/reject")
async def reject_action(
    case_id: str,
    request: RejectActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending recommendation."""
    case_result = await db.execute(select(RecoveryCase).where(RecoveryCase.id == case_id))
    case = case_result.scalar_one_or_none()
    if not case:
        raise NotFoundError("RecoveryCase", case_id)

    rec_result = await db.execute(
        select(RecoveryRecommendation)
        .where(RecoveryRecommendation.id == request.recommendation_id)
    )
    rec = rec_result.scalar_one_or_none()
    if rec:
        rec.status = "rejected"
        db.add(rec)

    approval = ApprovalRecord(
        recovery_case_id=case_id,
        recommendation_id=request.recommendation_id,
        status="rejected",
        approver_id=request.approver_id,
        approver_note=request.reason,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(approval)

    case.state = "HUMAN_REVIEW"
    db.add(case)

    audit = AuditService(db)
    await audit.record(
        "REJECTED",
        transaction_id=case.transaction_id,
        recovery_case_id=case_id,
        actor=request.approver_id or "system_user",
        previous_state="APPROVAL_REQUIRED",
        new_state="HUMAN_REVIEW",
        approval_details={"reason": request.reason},
    )
    await db.flush()

    return {"status": "rejected", "case_id": case_id, "new_state": case.state}


@router.post("/{case_id}/flag-review")
async def flag_for_review(
    case_id: str,
    reason: str = "Manual escalation",
    db: AsyncSession = Depends(get_db),
):
    """Flag a recovery case for human review."""
    case_result = await db.execute(select(RecoveryCase).where(RecoveryCase.id == case_id))
    case = case_result.scalar_one_or_none()
    if not case:
        raise NotFoundError("RecoveryCase", case_id)

    case.state = "HUMAN_REVIEW"
    case.requires_human_review = True
    case.human_review_reason = reason
    db.add(case)

    audit = AuditService(db)
    await audit.record(
        "HUMAN_REVIEW",
        transaction_id=case.transaction_id,
        recovery_case_id=case_id,
        actor="system_user",
        new_state="HUMAN_REVIEW",
        detected_risk=reason,
    )
    await db.flush()

    return {"status": "flagged_for_review", "case_id": case_id}
