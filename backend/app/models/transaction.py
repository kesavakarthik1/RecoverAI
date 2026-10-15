"""Core Transaction model."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    String, Boolean, Integer, Numeric, DateTime, Text, ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    __table_args__ = (
        Index("ix_transactions_merchant_status", "merchant_id", "status"),
        Index("ix_transactions_recovery_status", "recovery_status"),
        Index("ix_transactions_batch_id", "batch_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    batch_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Parties
    merchant_id: Mapped[str] = mapped_column(String(36), ForeignKey("merchants.id"), nullable=False)
    customer_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Financial — stored in smallest monetary unit for precision
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    # Classification
    transaction_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # payment | subscription | invoice | checkout

    # Status: pending | success | failed | abandoned | overdue | cancelled
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    # Failure information
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failure_category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # temp_failure | insufficient_funds | auth_required | invalid_details | fraud | unknown
    failure_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_eligible_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Risk scoring (0–100)
    risk_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Recovery classification: recoverable | non_recoverable | unknown | requires_review
    recoverability: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)

    # Recovery status: pending | in_progress | recovered | failed | blocked | human_review | closed
    recovery_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Ground truth for synthetic data evaluation
    synthetic_ground_truth_recoverable: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    synthetic_recovery_outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadata
    payment_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gateway: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    merchant: Mapped["Merchant"] = relationship(back_populates="transactions")
    recovery_case: Mapped[Optional["RecoveryCase"]] = relationship(
        back_populates="transaction", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} status={self.status} amount={self.amount}>"
