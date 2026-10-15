"""Evaluation Result — per-transaction result within an evaluation run."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class EvaluationResult(Base, TimestampMixin):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    evaluation_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_runs.id"), nullable=False, index=True
    )
    transaction_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Ground truth
    ground_truth_recoverable: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ground_truth_outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Model prediction
    predicted_recoverable: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    predicted_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    risk_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Action
    action_taken: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Outcome
    recovery_succeeded: Mapped[bool] = mapped_column(Boolean, default=False)
    recovered_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    at_risk_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    intervention_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)

    # Classification flags
    is_true_positive: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_false_positive: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_true_negative: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_false_negative: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    evaluation_run: Mapped["EvaluationRun"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<EvaluationResult id={self.id} txn={self.transaction_id} "
            f"recovered={self.recovery_succeeded}>"
        )
