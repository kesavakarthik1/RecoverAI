"""Customer reference model — stores anonymised customer metadata."""
from __future__ import annotations

from sqlalchemy import String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    # External reference — no real PII stored
    external_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    merchant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Communication preferences
    communication_consent: Mapped[bool] = mapped_column(Boolean, default=True)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    email_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_eligible: Mapped[bool] = mapped_column(Boolean, default=True)

    # Aggregate counters (denormalised for quick policy checks)
    reminder_count_7d: Mapped[int] = mapped_column(Integer, default=0)
    total_failed_payments: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<Customer id={self.id} ref={self.external_ref}>"
