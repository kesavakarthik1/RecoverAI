"""Policy configuration endpoints."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.policy_rule import PolicyRule
from app.models.merchant import Merchant

router = APIRouter()

DEFAULT_MERCHANT_ID = "merchant-demo-001"


class PolicyRuleUpdate(BaseModel):
    max_retry_attempts: Optional[int] = None
    min_retry_delay_hours: Optional[int] = None
    max_recovery_actions_per_txn: Optional[int] = None
    max_reminders_per_customer_per_week: Optional[int] = None
    require_communication_consent: Optional[bool] = None
    approval_threshold_amount: Optional[Decimal] = None
    retryable_failure_categories: Optional[List[str]] = None
    non_retryable_categories: Optional[List[str]] = None
    batch_max_actions: Optional[int] = None


async def _get_or_create_policy(db: AsyncSession, merchant_id: str) -> PolicyRule:
    result = await db.execute(
        select(PolicyRule).where(
            PolicyRule.merchant_id == merchant_id,
            PolicyRule.is_active == True,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        rule = PolicyRule(merchant_id=merchant_id, rule_set_name="default")
        db.add(rule)
        await db.flush()
    return rule


@router.get("")
async def get_policy(
    merchant_id: str = DEFAULT_MERCHANT_ID,
    db: AsyncSession = Depends(get_db),
):
    rule = await _get_or_create_policy(db, merchant_id)
    return {
        "id": rule.id,
        "merchant_id": rule.merchant_id,
        "rule_set_name": rule.rule_set_name,
        "max_retry_attempts": rule.max_retry_attempts,
        "min_retry_delay_hours": rule.min_retry_delay_hours,
        "max_recovery_actions_per_txn": rule.max_recovery_actions_per_txn,
        "max_reminders_per_customer_per_week": rule.max_reminders_per_customer_per_week,
        "require_communication_consent": rule.require_communication_consent,
        "approval_threshold_amount": float(rule.approval_threshold_amount),
        "retryable_failure_categories": rule.retryable_failure_categories,
        "non_retryable_categories": rule.non_retryable_categories,
        "batch_max_actions": rule.batch_max_actions,
        "updated_at": rule.updated_at.isoformat(),
    }


@router.put("")
async def update_policy(
    update: PolicyRuleUpdate,
    merchant_id: str = DEFAULT_MERCHANT_ID,
    db: AsyncSession = Depends(get_db),
):
    rule = await _get_or_create_policy(db, merchant_id)

    if update.max_retry_attempts is not None:
        rule.max_retry_attempts = update.max_retry_attempts
    if update.min_retry_delay_hours is not None:
        rule.min_retry_delay_hours = update.min_retry_delay_hours
    if update.max_recovery_actions_per_txn is not None:
        rule.max_recovery_actions_per_txn = update.max_recovery_actions_per_txn
    if update.max_reminders_per_customer_per_week is not None:
        rule.max_reminders_per_customer_per_week = update.max_reminders_per_customer_per_week
    if update.require_communication_consent is not None:
        rule.require_communication_consent = update.require_communication_consent
    if update.approval_threshold_amount is not None:
        rule.approval_threshold_amount = update.approval_threshold_amount
    if update.retryable_failure_categories is not None:
        rule.retryable_failure_categories = update.retryable_failure_categories
    if update.non_retryable_categories is not None:
        rule.non_retryable_categories = update.non_retryable_categories
    if update.batch_max_actions is not None:
        rule.batch_max_actions = update.batch_max_actions

    db.add(rule)
    await db.flush()

    return {"status": "updated", "policy_id": rule.id}


@router.post("/reset")
async def reset_policy_to_defaults(
    merchant_id: str = DEFAULT_MERCHANT_ID,
    db: AsyncSession = Depends(get_db),
):
    """Reset policy to safe defaults."""
    result = await db.execute(
        select(PolicyRule).where(PolicyRule.merchant_id == merchant_id)
    )
    rules = result.scalars().all()
    for rule in rules:
        await db.delete(rule)
    await db.flush()

    new_rule = PolicyRule(merchant_id=merchant_id, rule_set_name="default")
    db.add(new_rule)
    await db.flush()

    return {"status": "reset", "policy_id": new_rule.id}
