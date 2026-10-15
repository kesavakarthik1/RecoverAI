"""Dashboard metrics schema."""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict


class DashboardMetrics(BaseModel):
    # Volume
    total_transactions: int
    total_gross_value: Decimal
    total_revenue_at_risk: Decimal
    estimated_recoverable_value: Decimal
    actual_recovered_value: Decimal
    recovery_rate: Optional[Decimal] = None
    recovery_success_rate: Optional[Decimal] = None

    # Counts by status
    failed_payment_count: int
    abandoned_checkout_count: int
    failed_subscription_count: int
    overdue_receivable_count: int

    # Recovery execution
    recovery_actions_executed: int
    blocked_actions: int
    human_review_count: int

    # Trend data
    recovery_trend: List[Dict[str, Any]] = []
    failure_reason_distribution: List[Dict[str, Any]] = []
    revenue_at_risk_by_category: List[Dict[str, Any]] = []
    recovery_funnel: List[Dict[str, Any]] = []
    recent_activity: List[Dict[str, Any]] = []
    high_priority_cases: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)
