"""Recovery Recommendation — structured AI or rule-based recommendation."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, Numeric, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class RecoveryRecommendation(Base, TimestampMixin):
    __tablename__ = "recovery_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    recovery_case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recovery_cases.id"), nullable=False, index=True
    )
    transaction_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Recommendation fields
    recommended_action: Mapped[str] = mapped_column(String(100), nullable=False)
    # retry | send_reminder | request_auth | escalate | stop | human_review
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0.5)
    expected_recovery_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    estimated_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    potential_customer_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    policy_checks: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    blocking_conditions: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=False)

    # Source: rule_based | ai_assisted | ai_fallback
    source: Mapped[str] = mapped_column(String(50), default="rule_based")

    # Status: pending | approved | rejected | executed | superseded
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Relationships
    recovery_case: Mapped["RecoveryCase"] = relationship(back_populates="recommendations")

    def __repr__(self) -> str:
        return (
            f"<RecoveryRecommendation id={self.id} action={self.recommended_action}>"
        )
