"""Recovery Action — records a single executed or attempted recovery step."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, Numeric, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class RecoveryAction(Base, TimestampMixin):
    __tablename__ = "recovery_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    recovery_case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recovery_cases.id"), nullable=False, index=True
    )
    recommendation_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("recovery_recommendations.id"), nullable=True
    )
    transaction_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Idempotency
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Action type: retry | send_reminder | request_auth | escalate | stop | human_review
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Execution mode: simulated | razorpay_test | live (never 'live' in this project)
    execution_mode: Mapped[str] = mapped_column(String(50), default="simulated", nullable=False)

    # Status: pending | executing | succeeded | failed | blocked | skipped
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Policy decision
    policy_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_rule_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    policy_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution details
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Outcome
    recovered_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    is_duplicate_prevented: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    recovery_case: Mapped["RecoveryCase"] = relationship(back_populates="actions")

    def __repr__(self) -> str:
        return f"<RecoveryAction id={self.id} type={self.action_type} status={self.status}>"
