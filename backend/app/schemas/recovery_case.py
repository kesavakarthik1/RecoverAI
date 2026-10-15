"""Recovery case and action Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class RecoveryCaseSummary(BaseModel):
    id: str
    transaction_id: str
    merchant_id: str
    customer_ref: str
    category: str
    state: str
    at_risk_amount: Decimal
    currency: str
    estimated_recoverable_amount: Optional[Decimal] = None
    recovered_amount: Decimal
    priority: str
    risk_score: Optional[Decimal] = None
    requires_human_review: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecoveryRecommendationRead(BaseModel):
    id: str
    recommended_action: str
    reason: str
    evidence: Optional[str] = None
    confidence: Decimal
    expected_recovery_value: Optional[Decimal] = None
    estimated_cost: Optional[Decimal] = None
    potential_customer_impact: Optional[str] = None
    requires_human_approval: bool
    source: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecoveryActionRead(BaseModel):
    id: str
    action_type: str
    execution_mode: str
    status: str
    policy_allowed: bool
    policy_reason: Optional[str] = None
    executed_at: Optional[datetime] = None
    recovered_amount: Optional[Decimal] = None
    is_duplicate_prevented: bool
    error_details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecoveryCaseRead(BaseModel):
    id: str
    transaction_id: str
    merchant_id: str
    customer_ref: str
    batch_id: Optional[str] = None
    category: str
    state: str
    at_risk_amount: Decimal
    currency: str
    estimated_recoverable_amount: Optional[Decimal] = None
    recovered_amount: Decimal
    priority: str
    risk_score: Optional[Decimal] = None
    action_count: int
    requires_human_review: bool
    human_review_reason: Optional[str] = None
    close_reason: Optional[str] = None
    closed_at: Optional[datetime] = None
    is_simulated: bool
    created_at: datetime
    updated_at: datetime
    recommendations: List[RecoveryRecommendationRead] = []
    actions: List[RecoveryActionRead] = []

    model_config = ConfigDict(from_attributes=True)


class ApproveActionRequest(BaseModel):
    recommendation_id: str
    approver_id: Optional[str] = "system_user"
    note: Optional[str] = None


class RejectActionRequest(BaseModel):
    recommendation_id: str
    approver_id: Optional[str] = "system_user"
    reason: str
