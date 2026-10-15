"""Promise-to-Pay tracking model."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, Numeric, DateTime, Date, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class PromiseToPay(Base, TimestampMixin):
    __tablename__ = "promises_to_pay"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transactions.id"), nullable=True
    )
    invoice_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=True
    )
    merchant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    customer_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    promised_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    promised_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Status: pending | kept | broken | partial | cancelled
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    follow_up_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    last_follow_up_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PromiseToPay id={self.id} status={self.status}>"
