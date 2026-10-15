"""Invoice model for overdue receivables recovery."""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, Integer, Numeric, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    merchant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    customer_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    issued_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Status: unpaid | paid | overdue | disputed | cancelled | partial
    status: Mapped[str] = mapped_column(String(50), default="unpaid")

    days_overdue: Mapped[int] = mapped_column(Integer, default=0)
    reminder_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reminder_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Escalation: none | level1 | level2 | level3 | legal
    escalation_level: Mapped[str] = mapped_column(String(50), default="none")
    is_disputed: Mapped[bool] = mapped_column(Boolean, default=False)
    promise_to_pay_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} status={self.status} days_overdue={self.days_overdue}>"
