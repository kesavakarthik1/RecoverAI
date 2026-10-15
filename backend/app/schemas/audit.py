"""Audit event schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, Dict

from pydantic import BaseModel, ConfigDict


class AuditEventRead(BaseModel):
    id: str
    created_at: datetime
    batch_id: Optional[str] = None
    transaction_id: Optional[str] = None
    recovery_case_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    event_type: str
    actor: str
    detected_risk: Optional[str] = None
    evidence_used: Optional[Any] = None
    recommendation: Optional[str] = None
    policy_rules_evaluated: Optional[Any] = None
    policy_decision: Optional[str] = None
    approval_details: Optional[Any] = None
    action_attempted: Optional[str] = None
    execution_mode: Optional[str] = None
    action_result: Optional[Any] = None
    error_details: Optional[str] = None
    final_outcome: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
