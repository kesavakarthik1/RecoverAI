"""Checkout session model for abandonment recovery."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class CheckoutSession(Base, TimestampMixin):
    __tablename__ = "checkout_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transactions.id"), nullable=True
    )
    merchant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    customer_ref: Mapped[str] = mapped_column(String(255), nullable=False)

    cart_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    # Status: initiated | abandoned | completed | expired
    status: Mapped[str] = mapped_column(String(50), default="initiated")
    abandoned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Recovery info
    hours_since_abandonment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recovery_contact_count: Mapped[int] = mapped_column(Integer, default=0)
    last_contact_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    recovery_link_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<CheckoutSession id={self.id} status={self.status}>"
