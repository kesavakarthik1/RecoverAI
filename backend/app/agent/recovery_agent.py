"""
Recovery Agent — orchestrates the full detection-to-recovery lifecycle.

State machine:
  DETECTED → DIAGNOSED → RECOMMENDED → POLICY_CHECKED →
  APPROVAL_REQUIRED | APPROVED → EXECUTING →
  SUCCEEDED | FAILED | BLOCKED | HUMAN_REVIEW → CLOSED
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.ai_provider import AIProvider, get_ai_provider
from app.core.config import settings
from app.core.exceptions import DuplicateActionError
from app.core.logging import get_logger
from app.integrations.payment_provider import get_payment_provider
from app.models.audit_event import AuditEvent
from app.models.recovery_action import RecoveryAction
from app.models.recovery_case import RecoveryCase
from app.models.recovery_recommendation import RecoveryRecommendation
from app.models.transaction import Transaction
from app.policies.policy_engine import PolicyConfig, PolicyContext, PolicyEngine
from app.services.audit_service import AuditService
from app.services.risk_scoring import calculate_risk_score

logger = get_logger(__name__)


class RecoveryAgent:
    """
    Processes a single at-risk transaction through the recovery lifecycle.
    """

    def __init__(
        self,
        db: AsyncSession,
        ai_provider: Optional[AIProvider] = None,
        policy_config: Optional[PolicyConfig] = None,
        agent_run_id: Optional[str] = None,
        batch_action_count: int = 0,
    ) -> None:
        self.db = db
        self.ai = ai_provider or get_ai_provider()
        self.policy = PolicyEngine(policy_config)
        self.payment = get_payment_provider()
        self.audit = AuditService(db)
        self.agent_run_id = agent_run_id or str(uuid.uuid4())
        self.batch_action_count = batch_action_count

    async def process_transaction(
        self,
        transaction: Transaction,
        *,
        auto_execute: bool = True,
        batch_id: Optional[str] = None,
    ) -> RecoveryCase:
        """
        Full recovery lifecycle for one transaction.
        Returns the resulting RecoveryCase.
        """
        # ── 1. Create or load recovery case ──────────────────────────────────
        case = await self._get_or_create_case(transaction, batch_id=batch_id)

        if case.state in ("SUCCEEDED", "CLOSED"):
            logger.debug("Case already terminal", case_id=case.id, state=case.state)
            return case

        # ── 2. DETECTED → DIAGNOSED ──────────────────────────────────────────
        await self._diagnose(case, transaction)

        # ── 3. DIAGNOSED → RECOMMENDED ───────────────────────────────────────
        recommendation = await self._recommend(case, transaction)

        # ── 4. RECOMMENDED → POLICY_CHECKED ──────────────────────────────────
        policy_result = await self._check_policy(case, transaction, recommendation)

        if not policy_result.allowed:
            await self._block_case(case, transaction, recommendation, policy_result)
            return case

        # ── 5. Approval gate ─────────────────────────────────────────────────
        if policy_result.requires_approval and recommendation.requires_human_approval:
            await self._set_state(
                case, "APPROVAL_REQUIRED",
                event_type="APPROVAL_REQUIRED",
                transaction=transaction,
            )
            return case

        # ── 6. APPROVED → EXECUTING ──────────────────────────────────────────
        if auto_execute:
            await self._execute_action(case, transaction, recommendation)

        return case

    # ── Private lifecycle steps ───────────────────────────────────────────────

    async def _get_or_create_case(
        self, transaction: Transaction, batch_id: Optional[str]
    ) -> RecoveryCase:
        existing = await self.db.execute(
            select(RecoveryCase)
            .where(RecoveryCase.transaction_id == transaction.id)
            .options(
                selectinload(RecoveryCase.recommendations),
                selectinload(RecoveryCase.actions),
            )
        )
        case = existing.scalar_one_or_none()
        if case:
            return case

        # Determine category
        category = self._classify_category(transaction)

        case = RecoveryCase(
            transaction_id=transaction.id,
            merchant_id=transaction.merchant_id,
            customer_ref=transaction.customer_ref,
            batch_id=batch_id or transaction.batch_id,
            state="DETECTED",
            category=category,
            at_risk_amount=transaction.amount,
            currency=transaction.currency,
            priority="medium",
            is_simulated=True,
        )
        self.db.add(case)
        await self.db.flush()

        await self.audit.record(
            "DETECTED",
            transaction_id=transaction.id,
            recovery_case_id=case.id,
            batch_id=batch_id,
            agent_run_id=self.agent_run_id,
            new_state="DETECTED",
            detected_risk=f"Transaction {transaction.id} flagged as at-risk [{category}]",
        )
        return case

    def _classify_category(self, txn: Transaction) -> str:
        type_map = {
            "payment": "failed_payment",
            "checkout": "checkout_abandonment",
            "subscription": "failed_subscription",
            "invoice": "overdue_invoice",
        }
        return type_map.get(txn.transaction_type, "failed_payment")

    async def _diagnose(self, case: RecoveryCase, txn: Transaction) -> None:
        prev_state = case.state

        # Run risk scoring
        score_result = calculate_risk_score(
            failure_category=txn.failure_category,
            retry_count=txn.retry_count,
            amount=txn.amount,
            failure_timestamp=txn.failure_timestamp,
            transaction_type=txn.transaction_type,
            description=txn.description,
            max_retries=self.policy.config.max_retry_attempts,
        )

        # Update transaction risk fields
        txn.risk_score = score_result["risk_score"]
        txn.recoverability = score_result["recoverability"]
        self.db.add(txn)

        # Update case
        case.risk_score = score_result["risk_score"]
        case.priority = score_result["priority"]
        case.requires_human_review = score_result["requires_human_review"]
        if score_result["requires_human_review"]:
            case.human_review_reason = f"Risk scoring flagged: {', '.join(score_result['risk_factors'])}"

        # Estimated recoverable amount
        if txn.recoverability == "recoverable":
            recovery_rate = Decimal("0.40")  # Conservative 40% base estimate
            case.estimated_recoverable_amount = txn.amount * recovery_rate
        else:
            case.estimated_recoverable_amount = Decimal("0")

        case.state = "DIAGNOSED"
        self.db.add(case)
        await self.db.flush()

        await self.audit.record(
            "DIAGNOSED",
            transaction_id=txn.id,
            recovery_case_id=case.id,
            agent_run_id=self.agent_run_id,
            previous_state=prev_state,
            new_state="DIAGNOSED",
            evidence_used=score_result["risk_factors"],
            detected_risk=(
                f"Risk score: {score_result['risk_score']} | "
                f"Recoverability: {score_result['recoverability']} | "
                f"Priority: {score_result['priority']}"
            ),
        )

    async def _recommend(
        self, case: RecoveryCase, txn: Transaction
    ) -> RecoveryRecommendation:
        prev_state = case.state

        ai_ctx = {
            "transaction_id": txn.id,
            "transaction_type": txn.transaction_type,
            "failure_category": txn.failure_category,
            "failure_reason": txn.failure_reason,
            "retry_count": txn.retry_count,
            "max_retries": self.policy.config.max_retry_attempts,
            "amount": float(txn.amount),
            "currency": txn.currency,
            "risk_score": float(txn.risk_score) if txn.risk_score else None,
            "recoverability": txn.recoverability,
            "description": txn.description,
        }

        try:
            rec_out = await self.ai.get_recommendation(ai_ctx)
        except Exception as exc:
            logger.warning("AI recommendation failed, using fallback", error=str(exc))
            from app.agent.ai_provider import RuleBasedProvider
            fallback = RuleBasedProvider()
            rec_out = await fallback.get_recommendation(ai_ctx)
            rec_out.source = "ai_fallback"

        rec = RecoveryRecommendation(
            recovery_case_id=case.id,
            transaction_id=txn.id,
            recommended_action=rec_out.recommended_action,
            reason=rec_out.reason,
            evidence=rec_out.evidence,
            confidence=Decimal(str(round(rec_out.confidence, 4))),
            expected_recovery_value=rec_out.expected_recovery_value,
            estimated_cost=rec_out.estimated_cost,
            potential_customer_impact=rec_out.potential_customer_impact,
            requires_human_approval=rec_out.requires_human_approval,
            source=rec_out.source,
            status="pending",
        )
        self.db.add(rec)

        case.state = "RECOMMENDED"
        self.db.add(case)
        await self.db.flush()

        await self.audit.record(
            "RECOMMENDED",
            transaction_id=txn.id,
            recovery_case_id=case.id,
            agent_run_id=self.agent_run_id,
            previous_state=prev_state,
            new_state="RECOMMENDED",
            recommendation=(
                f"Action: {rec_out.recommended_action} | "
                f"Confidence: {rec_out.confidence:.0%} | "
                f"Source: {rec_out.source}"
            ),
        )
        return rec

    async def _check_policy(
        self,
        case: RecoveryCase,
        txn: Transaction,
        rec: RecoveryRecommendation,
    ):
        from app.policies.policy_engine import PolicyContext, PolicyResult

        prev_state = case.state

        ctx = PolicyContext(
            transaction_id=txn.id,
            merchant_id=txn.merchant_id,
            transaction_type=txn.transaction_type,
            failure_category=txn.failure_category,
            retry_count=txn.retry_count,
            amount=txn.amount,
            currency=txn.currency,
            recovery_status=txn.recovery_status,
            recoverability=txn.recoverability,
            action_count=case.action_count,
            last_retry_at=txn.last_retry_at,
            last_action_at=case.last_action_at,
            failure_timestamp=txn.failure_timestamp,
            batch_action_count=self.batch_action_count,
            description=txn.description,
        )

        result = self.policy.evaluate(ctx, rec.recommended_action)

        case.state = "POLICY_CHECKED"
        rec.policy_checks = result.blocking_rules or ["ALLOWED"]
        self.db.add(case)
        self.db.add(rec)
        await self.db.flush()

        await self.audit.record(
            "POLICY_CHECKED",
            transaction_id=txn.id,
            recovery_case_id=case.id,
            agent_run_id=self.agent_run_id,
            previous_state=prev_state,
            new_state="POLICY_CHECKED",
            policy_rules_evaluated=result.blocking_rules or ["ALLOWED"],
            policy_decision="allowed" if result.allowed else "blocked",
            recommendation=f"Policy: {result.reason}",
        )
        return result

    async def _block_case(
        self,
        case: RecoveryCase,
        txn: Transaction,
        rec: RecoveryRecommendation,
        policy_result,
    ) -> None:
        prev_state = case.state
        case.state = "BLOCKED"
        txn.recovery_status = "blocked"
        rec.status = "rejected"

        # Create blocked action record
        idempotency_key = f"block-{txn.id}-{case.action_count}"
        action = RecoveryAction(
            recovery_case_id=case.id,
            recommendation_id=rec.id,
            transaction_id=txn.id,
            idempotency_key=idempotency_key,
            action_type=rec.recommended_action,
            execution_mode="simulated",
            status="blocked",
            policy_allowed=False,
            policy_rule_id=policy_result.rule_id,
            policy_reason=policy_result.reason,
        )
        self.db.add(action)
        self.db.add(case)
        self.db.add(txn)
        self.db.add(rec)
        await self.db.flush()

        await self.audit.record(
            "BLOCKED",
            transaction_id=txn.id,
            recovery_case_id=case.id,
            agent_run_id=self.agent_run_id,
            previous_state=prev_state,
            new_state="BLOCKED",
            policy_decision="blocked",
            action_attempted=rec.recommended_action,
            final_outcome="BLOCKED",
            error_details=f"Policy [{policy_result.rule_id}]: {policy_result.reason}",
        )

    async def _execute_action(
        self,
        case: RecoveryCase,
        txn: Transaction,
        rec: RecoveryRecommendation,
    ) -> None:
        prev_state = case.state

        # Idempotency check
        idempotency_key = f"{rec.recommended_action}-{txn.id}-attempt-{txn.retry_count}"
        existing_action = await self.db.execute(
            select(RecoveryAction).where(
                RecoveryAction.idempotency_key == idempotency_key
            )
        )
        if existing_action.scalar_one_or_none():
            logger.warning("Duplicate action prevented", key=idempotency_key)
            action = RecoveryAction(
                recovery_case_id=case.id,
                recommendation_id=rec.id,
                transaction_id=txn.id,
                idempotency_key=f"{idempotency_key}-dup-{uuid.uuid4().hex[:8]}",
                action_type=rec.recommended_action,
                execution_mode="simulated",
                status="skipped",
                policy_allowed=True,
                policy_reason="Duplicate action prevented by idempotency key",
                is_duplicate_prevented=True,
            )
            self.db.add(action)
            await self.db.flush()
            return

        case.state = "EXECUTING"
        self.db.add(case)
        await self.db.flush()

        # Create action record
        action = RecoveryAction(
            recovery_case_id=case.id,
            recommendation_id=rec.id,
            transaction_id=txn.id,
            idempotency_key=idempotency_key,
            action_type=rec.recommended_action,
            execution_mode=settings.PAYMENT_PROVIDER,
            status="executing",
            policy_allowed=True,
        )
        self.db.add(action)
        await self.db.flush()

        # Execute via payment provider
        try:
            result = await self.payment.execute_action(
                action_type=rec.recommended_action,
                transaction_id=txn.id,
                amount=txn.amount,
                currency=txn.currency,
                metadata={
                    "failure_category": txn.failure_category,
                    "retry_count": txn.retry_count,
                    "recovery_case_id": case.id,
                },
            )
            success = result.get("success", False)
        except Exception as exc:
            logger.error("Payment provider error", error=str(exc))
            result = {"success": False, "error": str(exc)}
            success = False

        now = datetime.now(timezone.utc)
        action.executed_at = now
        action.result = result
        case.last_action_at = now
        case.action_count += 1
        self.batch_action_count += 1

        if rec.recommended_action == "human_review":
            action.status = "succeeded"
            case.state = "HUMAN_REVIEW"
            txn.recovery_status = "human_review"
            case.requires_human_review = True
        elif success:
            action.status = "succeeded"
            action.recovered_amount = txn.amount
            case.state = "SUCCEEDED"
            case.recovered_amount = txn.amount
            txn.recovery_status = "recovered"
            txn.status = "success"
            rec.status = "executed"
        else:
            action.status = "failed"
            case.state = "FAILED"
            txn.recovery_status = "failed"

        # Update retry count for retry actions
        if rec.recommended_action == "retry":
            txn.retry_count += 1
            txn.last_retry_at = now

        self.db.add(action)
        self.db.add(case)
        self.db.add(txn)
        self.db.add(rec)
        await self.db.flush()

        await self.audit.record(
            "SUCCEEDED" if success else ("HUMAN_REVIEW" if case.state == "HUMAN_REVIEW" else "FAILED"),
            transaction_id=txn.id,
            recovery_case_id=case.id,
            agent_run_id=self.agent_run_id,
            previous_state=prev_state,
            new_state=case.state,
            action_attempted=rec.recommended_action,
            execution_mode=settings.PAYMENT_PROVIDER,
            action_result=result,
            final_outcome=case.state,
        )

    async def _set_state(
        self,
        case: RecoveryCase,
        new_state: str,
        event_type: str,
        transaction: Transaction,
    ) -> None:
        prev = case.state
        case.state = new_state
        self.db.add(case)
        await self.db.flush()
        await self.audit.record(
            event_type,
            transaction_id=transaction.id,
            recovery_case_id=case.id,
            agent_run_id=self.agent_run_id,
            previous_state=prev,
            new_state=new_state,
        )
