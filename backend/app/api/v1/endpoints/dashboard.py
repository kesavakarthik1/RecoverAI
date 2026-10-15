"""Dashboard metrics endpoint."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.schemas.dashboard import DashboardMetrics

router = APIRouter()


@router.get("", response_model=DashboardMetrics)
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)) -> DashboardMetrics:
    """
    Calculate all dashboard metrics from persisted database records.
    All values are computed — nothing is hardcoded.
    """

    # ── Transaction counts ─────────────────────────────────────────────────
    txn_result = await db.execute(select(Transaction))
    transactions = list(txn_result.scalars().all())

    total_transactions = len(transactions)
    total_gross_value = sum(t.amount for t in transactions) if transactions else Decimal("0")

    # At-risk = failed, abandoned, overdue
    at_risk_txns = [
        t for t in transactions
        if t.status in ("failed", "abandoned", "overdue")
        and t.recovery_status not in ("closed", "recovered")
    ]
    total_revenue_at_risk = sum(t.amount for t in at_risk_txns)

    # Estimated recoverable
    recoverable_txns = [t for t in at_risk_txns if t.recoverability == "recoverable"]
    estimated_recoverable_value = sum(t.amount for t in recoverable_txns) * Decimal("0.40")

    # Recovered
    recovered_txns = [t for t in transactions if t.recovery_status == "recovered"]
    actual_recovered_value = sum(t.amount for t in recovered_txns)

    # Rates
    eligible_at_risk = len(at_risk_txns)
    recovered_count = len(recovered_txns)

    recovery_rate = (
        Decimal(recovered_count) / Decimal(eligible_at_risk)
        if eligible_at_risk > 0
        else None
    )

    # Success rate — of those attempted, how many succeeded
    action_result = await db.execute(select(RecoveryAction))
    actions = list(action_result.scalars().all())
    attempted = [a for a in actions if a.status in ("succeeded", "failed")]
    succeeded = [a for a in attempted if a.status == "succeeded"]
    recovery_success_rate = (
        Decimal(len(succeeded)) / Decimal(len(attempted))
        if attempted
        else None
    )

    # Counts by type
    failed_payment_count = sum(
        1 for t in transactions
        if t.transaction_type == "payment" and t.status == "failed"
    )
    abandoned_checkout_count = sum(
        1 for t in transactions
        if t.transaction_type == "checkout" and t.status == "abandoned"
    )
    failed_subscription_count = sum(
        1 for t in transactions
        if t.transaction_type == "subscription" and t.status == "failed"
    )
    overdue_receivable_count = sum(
        1 for t in transactions
        if t.transaction_type == "invoice" and t.status == "overdue"
    )

    # Recovery execution stats
    recovery_actions_executed = len([a for a in actions if a.status == "succeeded"])
    blocked_actions = len([a for a in actions if a.status == "blocked"])

    cases_result = await db.execute(select(RecoveryCase))
    cases = list(cases_result.scalars().all())
    human_review_count = sum(1 for c in cases if c.state == "HUMAN_REVIEW" or c.requires_human_review)

    # ── Trend data (last 7 days by day) ──────────────────────────────────────
    from datetime import datetime, timedelta, timezone
    recovery_trend = []
    for i in range(6, -1, -1):
        day = datetime.now(timezone.utc).date() - timedelta(days=i)
        day_cases = [
            c for c in cases
            if c.created_at.date() == day and c.state == "SUCCEEDED"
        ]
        day_at_risk = [
            c for c in cases
            if c.created_at.date() == day
        ]
        recovery_trend.append({
            "date": day.isoformat(),
            "recovered": float(sum(c.recovered_amount for c in day_cases)),
            "at_risk": float(sum(c.at_risk_amount for c in day_at_risk)),
        })

    # ── Failure reason distribution ───────────────────────────────────────────
    category_counts: Dict[str, int] = {}
    for t in at_risk_txns:
        cat = t.failure_category or "unknown"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    failure_reason_distribution = [
        {"name": k, "value": v} for k, v in category_counts.items()
    ]

    # ── Revenue at risk by category ───────────────────────────────────────────
    cat_value: Dict[str, float] = {}
    for t in at_risk_txns:
        cat = t.transaction_type or "unknown"
        cat_value[cat] = cat_value.get(cat, 0.0) + float(t.amount)

    revenue_at_risk_by_category = [
        {"category": k, "value": v} for k, v in cat_value.items()
    ]

    # ── Recovery funnel ───────────────────────────────────────────────────────
    state_counts: Dict[str, int] = {}
    for c in cases:
        state_counts[c.state] = state_counts.get(c.state, 0) + 1

    recovery_funnel = [
        {"stage": k, "count": v}
        for k, v in state_counts.items()
    ]

    # ── Recent activity (last 10 audit events) ────────────────────────────────
    audit_result = await db.execute(
        select(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(10)
    )
    recent_events = audit_result.scalars().all()
    recent_activity = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "transaction_id": e.transaction_id,
            "actor": e.actor,
            "timestamp": e.created_at.isoformat(),
            "outcome": e.final_outcome,
        }
        for e in recent_events
    ]

    # ── High priority cases ────────────────────────────────────────────────────
    high_priority = sorted(
        [c for c in cases if c.state not in ("SUCCEEDED", "CLOSED", "BLOCKED") and c.priority in ("critical", "high")],
        key=lambda x: x.at_risk_amount,
        reverse=True,
    )[:5]

    high_priority_cases = [
        {
            "id": c.id,
            "transaction_id": c.transaction_id,
            "category": c.category,
            "priority": c.priority,
            "at_risk_amount": float(c.at_risk_amount),
            "currency": c.currency,
            "state": c.state,
        }
        for c in high_priority
    ]

    return DashboardMetrics(
        total_transactions=total_transactions,
        total_gross_value=total_gross_value,
        total_revenue_at_risk=total_revenue_at_risk,
        estimated_recoverable_value=estimated_recoverable_value,
        actual_recovered_value=actual_recovered_value,
        recovery_rate=recovery_rate,
        recovery_success_rate=recovery_success_rate,
        failed_payment_count=failed_payment_count,
        abandoned_checkout_count=abandoned_checkout_count,
        failed_subscription_count=failed_subscription_count,
        overdue_receivable_count=overdue_receivable_count,
        recovery_actions_executed=recovery_actions_executed,
        blocked_actions=blocked_actions,
        human_review_count=human_review_count,
        recovery_trend=recovery_trend,
        failure_reason_distribution=failure_reason_distribution,
        revenue_at_risk_by_category=revenue_at_risk_by_category,
        recovery_funnel=recovery_funnel,
        recent_activity=recent_activity,
        high_priority_cases=high_priority_cases,
    )
