"""Evaluation Run — tracks a batch evaluation experiment."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, Integer, Numeric, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    batch_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Strategy: baseline | fixed_rule | ai_assisted
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, default=42)

    # Status: pending | running | completed | failed
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Aggregate metrics ──────────────────────────────────────────────────────
    total_transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    total_transaction_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    eligible_at_risk_count: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue_at_risk: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    estimated_recoverable_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    successful_recoveries: Mapped[int] = mapped_column(Integer, default=0)
    simulated_recovered_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    recovery_rate_by_count: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), nullable=True)
    recovery_rate_by_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), nullable=True)
    retry_success_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), nullable=True)
    action_failure_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), nullable=True)

    blocked_action_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_prevented_count: Mapped[int] = mapped_column(Integer, default=0)
    human_review_count: Mapped[int] = mapped_column(Integer, default=0)
    customer_contact_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_intervention_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    net_simulated_recovery_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    false_positive_intervention_count: Mapped[int] = mapped_column(Integer, default=0)

    # Classification metrics (when ground truth is available)
    precision: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), nullable=True)
    recall: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), nullable=True)
    false_positive_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), nullable=True)

    # Breakdown by category and strategy (JSON)
    results_by_category: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    results_by_strategy: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<EvaluationRun id={self.id} strategy={self.strategy} status={self.status}>"
