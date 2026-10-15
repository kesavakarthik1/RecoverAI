"""
Append-only audit event log.
Application code must NEVER update or delete rows from this table.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import generate_uuid


class AuditEvent(Base):
    """
    Append-only audit trail.
    No updated_at — rows are never modified after insertion.
    """

    __tablename__ = "audit_events"

    __table_args__ = (
        Index("ix_audit_events_txn_id", "transaction_id"),
        Index("ix_audit_events_case_id", "recovery_case_id"),
        Index("ix_audit_events_batch_id", "batch_id"),
        Index("ix_audit_events_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Context
    batch_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    recovery_case_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("recovery_cases.id"), nullable=True
    )
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # State transition
    previous_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    new_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Event details
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # DETECTED | DIAGNOSED | RECOMMENDED | POLICY_CHECKED | APPROVED | REJECTED |
    # EXECUTING | SUCCEEDED | FAILED | BLOCKED | HUMAN_REVIEW | CLOSED |
    # IMPORT | EVALUATION | CONFIG_CHANGE

    actor: Mapped[str] = mapped_column(String(255), default="system", nullable=False)

    # Evidence and reasoning
    detected_risk: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_used: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Policy
    policy_rules_evaluated: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    policy_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Approval
    approval_details: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    # Action result
    action_attempted: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    execution_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    action_result: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Final outcome
    final_outcome: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata_: Mapped[Optional[str]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    recovery_case: Mapped[Optional["RecoveryCase"]] = relationship(
        back_populates="audit_events"
    )

    def __repr__(self) -> str:
        return f"<AuditEvent id={self.id} type={self.event_type} txn={self.transaction_id}>"
