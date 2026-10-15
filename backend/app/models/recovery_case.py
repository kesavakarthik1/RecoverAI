"""Recovery Case — tracks the full lifecycle of a recovery attempt."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, Numeric, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class RecoveryCase(Base, TimestampMixin):
    __tablename__ = "recovery_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id"), nullable=False, unique=True, index=True
    )
    merchant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    customer_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    batch_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # State machine:
    # DETECTED → DIAGNOSED → RECOMMENDED → POLICY_CHECKED →
    # APPROVAL_REQUIRED | APPROVED → EXECUTING →
    # SUCCEEDED | FAILED | BLOCKED | HUMAN_REVIEW → CLOSED
    state: Mapped[str] = mapped_column(String(50), default="DETECTED", nullable=False, index=True)

    # Category: failed_payment | checkout_abandonment | failed_subscription | overdue_invoice
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Financial
    at_risk_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    estimated_recoverable_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    recovered_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)

    # Priority: critical | high | medium | low
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    risk_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Action tracking
    action_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_action_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_eligible_action_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Outcome
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    human_review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Simulation tracking
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="recovery_case")
    recommendations: Mapped[list["RecoveryRecommendation"]] = relationship(
        back_populates="recovery_case", order_by="RecoveryRecommendation.created_at"
    )
    actions: Mapped[list["RecoveryAction"]] = relationship(
        back_populates="recovery_case", order_by="RecoveryAction.created_at"
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="recovery_case", order_by="AuditEvent.created_at"
    )

    def __repr__(self) -> str:
        return f"<RecoveryCase id={self.id} state={self.state} category={self.category}>"
