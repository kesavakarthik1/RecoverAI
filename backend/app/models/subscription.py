"""Subscription model for recurring payment recovery."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    merchant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    customer_ref: Mapped[str] = mapped_column(String(255), nullable=False)

    plan_name: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    billing_cycle: Mapped[str] = mapped_column(String(50), default="monthly")

    # Status: active | paused | cancelled | past_due | expired
    status: Mapped[str] = mapped_column(String(50), default="active")

    next_billing_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_payment_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} status={self.status}>"
