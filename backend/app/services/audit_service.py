"""
Audit Service — creates append-only audit events.
All recovery actions must be traceable through this service.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        event_type: str,
        *,
        transaction_id: Optional[str] = None,
        recovery_case_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        agent_run_id: Optional[str] = None,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        actor: str = "system",
        detected_risk: Optional[str] = None,
        evidence_used: Optional[Any] = None,
        recommendation: Optional[str] = None,
        policy_rules_evaluated: Optional[Any] = None,
        policy_decision: Optional[str] = None,
        approval_details: Optional[Any] = None,
        action_attempted: Optional[str] = None,
        execution_mode: Optional[str] = None,
        action_result: Optional[Any] = None,
        error_details: Optional[str] = None,
        final_outcome: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Create and persist an immutable audit event."""
        event = AuditEvent(
            event_type=event_type,
            transaction_id=transaction_id,
            recovery_case_id=recovery_case_id,
            batch_id=batch_id,
            agent_run_id=agent_run_id,
            previous_state=previous_state,
            new_state=new_state,
            actor=actor,
            detected_risk=detected_risk,
            evidence_used=evidence_used,
            recommendation=recommendation,
            policy_rules_evaluated=policy_rules_evaluated,
            policy_decision=policy_decision,
            approval_details=approval_details,
            action_attempted=action_attempted,
            execution_mode=execution_mode,
            action_result=action_result,
            error_details=error_details,
            final_outcome=final_outcome,
            metadata_=metadata,
        )
        self.db.add(event)
        await self.db.flush()  # Assign ID without committing
        logger.debug(
            "Audit event recorded",
            event_id=event.id,
            event_type=event_type,
            transaction_id=transaction_id,
        )
        return event
