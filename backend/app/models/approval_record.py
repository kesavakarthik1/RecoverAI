"""Approval Record — human approval decisions for high-value recovery actions."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class ApprovalRecord(Base, TimestampMixin):
    __tablename__ = "approval_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    recovery_case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recovery_cases.id"), nullable=False, index=True
    )
    recommendation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recovery_recommendations.id"), nullable=False
    )

    # Status: pending | approved | rejected
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    approver_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approver_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # The action that was triggered on approval
    triggered_action_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    def __repr__(self) -> str:
        return f"<ApprovalRecord id={self.id} status={self.status}>"
