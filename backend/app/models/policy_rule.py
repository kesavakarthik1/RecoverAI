"""Policy Rule — configurable recovery policy parameters per merchant."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, Integer, Numeric, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class PolicyRule(Base, TimestampMixin):
    __tablename__ = "policy_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    merchant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("merchants.id"), nullable=False, index=True
    )
    rule_set_name: Mapped[str] = mapped_column(String(100), default="default", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Retry limits
    max_retry_attempts: Mapped[int] = mapped_column(Integer, default=3)
    min_retry_delay_hours: Mapped[int] = mapped_column(Integer, default=24)
    max_recovery_actions_per_txn: Mapped[int] = mapped_column(Integer, default=5)

    # Communication limits
    max_reminders_per_customer_per_week: Mapped[int] = mapped_column(Integer, default=2)
    require_communication_consent: Mapped[bool] = mapped_column(Boolean, default=True)

    # Approval thresholds (INR)
    approval_threshold_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=50000)

    # Retry eligibility by failure category (JSON list of eligible categories)
    retryable_failure_categories: Mapped[Optional[str]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: ["temp_failure"],
    )

    # Non-retryable categories (JSON list)
    non_retryable_categories: Mapped[Optional[str]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: ["fraud", "invalid_details"],
    )

    # Batch limits
    batch_max_actions: Mapped[int] = mapped_column(Integer, default=500)

    # Human review conditions (JSON list)
    human_review_conditions: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    merchant: Mapped["Merchant"] = relationship(back_populates="policy_rules")

    def __repr__(self) -> str:
        return f"<PolicyRule id={self.id} merchant={self.merchant_id}>"
