"""Evaluation schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from pydantic import BaseModel, ConfigDict


class EvaluationRunRead(BaseModel):
    id: str
    name: str
    strategy: str
    status: str
    random_seed: int
    total_transaction_count: int
    total_transaction_value: Decimal
    eligible_at_risk_count: int
    total_revenue_at_risk: Decimal
    estimated_recoverable_value: Decimal
    successful_recoveries: int
    simulated_recovered_value: Decimal
    recovery_rate_by_count: Optional[Decimal] = None
    recovery_rate_by_value: Optional[Decimal] = None
    retry_success_rate: Optional[Decimal] = None
    action_failure_rate: Optional[Decimal] = None
    blocked_action_count: int
    duplicate_prevented_count: int
    human_review_count: int
    customer_contact_count: int
    estimated_intervention_cost: Decimal
    net_simulated_recovery_value: Decimal
    false_positive_intervention_count: int
    precision: Optional[Decimal] = None
    recall: Optional[Decimal] = None
    false_positive_rate: Optional[Decimal] = None
    results_by_category: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyComparisonResponse(BaseModel):
    baseline: Optional[EvaluationRunRead] = None
    fixed_rule: Optional[EvaluationRunRead] = None
    ai_assisted: Optional[EvaluationRunRead] = None
    comparison_table: Optional[list] = None
