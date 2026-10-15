"""
Batch Evaluation Engine.

Processes a labeled synthetic dataset through three strategies:
  1. baseline    — no automated recovery
  2. fixed_rule  — deterministic rule-based recovery
  3. ai_assisted — AI-assisted + deterministic policy enforcement

Measures all 20 required metrics.
Uses consistent random seed and dataset across strategies for fair comparison.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.payment_provider import SimulationProvider
from app.models.evaluation_result import EvaluationResult
from app.models.evaluation_run import EvaluationRun
from app.models.transaction import Transaction
from app.policies.policy_engine import PolicyConfig, PolicyContext, PolicyEngine
from app.services.risk_scoring import calculate_risk_score

logger = get_logger(__name__)

# Cost per intervention type (INR)
INTERVENTION_COSTS = {
    "retry": Decimal("5"),
    "send_reminder": Decimal("2"),
    "request_auth": Decimal("3"),
    "escalate": Decimal("10"),
    "human_review": Decimal("25"),
    "stop": Decimal("0"),
    "none": Decimal("0"),
}

CONTACT_ACTIONS = {"send_reminder", "request_auth", "escalate"}


class EvaluationEngine:
    def __init__(self, db: AsyncSession, seed: int = 42) -> None:
        self.db = db
        self.seed = seed
        self._payment_sim = SimulationProvider(seed=seed)
        self._policy = PolicyEngine(PolicyConfig())

    async def run_comparison(
        self,
        batch_id: Optional[str] = None,
        transaction_ids: Optional[List[str]] = None,
        name_prefix: str = "Evaluation",
    ) -> Dict[str, EvaluationRun]:
        """Run all three strategies on the same dataset."""
        transactions = await self._load_transactions(batch_id, transaction_ids)
        if not transactions:
            raise ValueError("No transactions found for evaluation")

        logger.info(
            "Starting strategy comparison",
            txn_count=len(transactions),
            batch_id=batch_id,
        )

        results = {}
        for strategy in ["baseline", "fixed_rule", "ai_assisted"]:
            run = await self._run_strategy(
                transactions=transactions,
                strategy=strategy,
                name=f"{name_prefix} — {strategy}",
                batch_id=batch_id,
            )
            results[strategy] = run

        return results

    async def _load_transactions(
        self,
        batch_id: Optional[str],
        transaction_ids: Optional[List[str]],
    ) -> List[Transaction]:
        if transaction_ids:
            result = await self.db.execute(
                select(Transaction).where(Transaction.id.in_(transaction_ids))
            )
        elif batch_id:
            result = await self.db.execute(
                select(Transaction).where(Transaction.batch_id == batch_id)
            )
        else:
            result = await self.db.execute(select(Transaction).limit(200))
        return list(result.scalars().all())

    async def _run_strategy(
        self,
        transactions: List[Transaction],
        strategy: str,
        name: str,
        batch_id: Optional[str],
    ) -> EvaluationRun:
        run = EvaluationRun(
            name=name,
            strategy=strategy,
            batch_id=batch_id,
            random_seed=self.seed,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        await self.db.flush()

        try:
            tx_results = []
            for txn in transactions:
                tx_result = await self._evaluate_transaction(txn, strategy, run.id)
                tx_results.append(tx_result)
                self.db.add(tx_result)

            await self.db.flush()
            metrics = self._calculate_metrics(tx_results, transactions)
            self._populate_run_metrics(run, metrics)
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            logger.error("Evaluation run failed", strategy=strategy, error=str(exc))
            run.status = "failed"
            run.error_message = str(exc)

        self.db.add(run)
        await self.db.flush()
        return run

    async def _evaluate_transaction(
        self,
        txn: Transaction,
        strategy: str,
        run_id: str,
    ) -> EvaluationResult:
        result = EvaluationResult(
            evaluation_run_id=run_id,
            transaction_id=txn.id,
            ground_truth_recoverable=txn.synthetic_ground_truth_recoverable,
            ground_truth_outcome=txn.synthetic_recovery_outcome,
            at_risk_amount=txn.amount,
        )

        # ── Baseline: no action ─────────────────────────────────────────────
        if strategy == "baseline":
            result.action_taken = "none"
            result.action_blocked = False
            result.recovery_succeeded = False
            result.recovered_amount = Decimal("0")
            result.intervention_cost = Decimal("0")
            result.predicted_recoverable = False
            result.predicted_category = txn.failure_category
            self._compute_classification(result)
            return result

        # ── Score and categorise ─────────────────────────────────────────────
        score = calculate_risk_score(
            failure_category=txn.failure_category,
            retry_count=txn.retry_count,
            amount=txn.amount,
            failure_timestamp=txn.failure_timestamp,
            transaction_type=txn.transaction_type,
            description=txn.description,
            max_retries=3,
        )
        result.risk_score = score["risk_score"]
        result.predicted_recoverable = score["recoverability"] == "recoverable"
        result.predicted_category = txn.failure_category

        # Determine action
        if strategy == "fixed_rule":
            action = self._select_fixed_rule_action(txn, score)
        else:  # ai_assisted (also deterministic here — same as rule-based but with confidence weights)
            action = self._select_ai_assisted_action(txn, score)

        # Policy check
        ctx = PolicyContext(
            transaction_id=txn.id,
            merchant_id=txn.merchant_id,
            transaction_type=txn.transaction_type,
            failure_category=txn.failure_category,
            retry_count=txn.retry_count,
            amount=txn.amount,
            currency=txn.currency,
            recovery_status=txn.recovery_status,
            recoverability=score["recoverability"],
            action_count=0,
            description=txn.description,
        )
        policy_result = self._policy.evaluate(ctx, action)

        if not policy_result.allowed:
            result.action_taken = action
            result.action_blocked = True
            result.block_reason = policy_result.reason
            result.recovery_succeeded = False
            result.recovered_amount = Decimal("0")
            result.intervention_cost = Decimal("0")
            self._compute_classification(result)
            return result

        result.action_taken = action
        result.action_blocked = False
        result.intervention_cost = INTERVENTION_COSTS.get(action, Decimal("5"))

        # Simulate outcome
        sim_result = await self._payment_sim.execute_action(
            action_type=action,
            transaction_id=txn.id,
            amount=txn.amount,
            currency=txn.currency,
            metadata={"failure_category": txn.failure_category},
        )
        success = sim_result.get("success", False)

        result.recovery_succeeded = success
        result.recovered_amount = txn.amount if success else Decimal("0")

        self._compute_classification(result)
        return result

    def _select_fixed_rule_action(
        self, txn: Transaction, score: Dict[str, Any]
    ) -> str:
        """Deterministic rule-based action selection."""
        cat = (txn.failure_category or "unknown").lower()
        rec = score["recoverability"]
        desc = (txn.description or "").lower()

        if rec == "non_recoverable" or cat in ("fraud", "invalid_details"):
            return "stop"
        if "cancelled_subscription" in desc:
            return "stop"
        if "disputed_invoice" in desc:
            return "human_review"
        if "opted_out_customer" in desc:
            return "stop"
        if rec == "requires_review" or cat == "unknown":
            return "human_review"
        if cat == "auth_required":
            return "request_auth"
        if cat == "temp_failure" and txn.retry_count < 3:
            return "retry"
        if txn.transaction_type in ("checkout", "invoice"):
            return "send_reminder"
        return "human_review"

    def _select_ai_assisted_action(
        self, txn: Transaction, score: Dict[str, Any]
    ) -> str:
        """
        AI-assisted selection — in evaluation mode we use the same logic
        as fixed_rule but with confidence-adjusted thresholds.
        In production the LLM would be called; here we use risk_score weighting.
        """
        base_action = self._select_fixed_rule_action(txn, score)
        risk = float(score["risk_score"])

        # AI assists by escalating borderline cases to human review
        if base_action == "retry" and risk > 70:
            return "escalate"
        if base_action == "send_reminder" and risk > 75:
            return "escalate"
        return base_action

    def _compute_classification(self, result: EvaluationResult) -> None:
        """Compute TP/FP/TN/FN flags using ground truth labels."""
        gt = result.ground_truth_recoverable
        pred = result.predicted_recoverable

        if gt is None:
            return  # No ground truth available

        if pred is True and gt is True:
            result.is_true_positive = True
        elif pred is True and gt is False:
            result.is_false_positive = True
        elif pred is False and gt is False:
            result.is_true_negative = True
        elif pred is False and gt is True:
            result.is_false_negative = True

    def _calculate_metrics(
        self,
        results: List[EvaluationResult],
        transactions: List[Transaction],
    ) -> Dict[str, Any]:
        total = len(transactions)
        total_value = sum(t.amount for t in transactions)

        # Eligible at-risk = excluded non_applicable and already closed
        eligible = [
            r for r in results
            if r.ground_truth_recoverable is not None
            or (r.ground_truth_recoverable is None and r.action_taken != "none")
        ]
        # More precise: those that were actually at-risk
        at_risk_results = [
            r for r in results
            if (r.ground_truth_outcome or "") not in ("not_applicable", "")
            and r.at_risk_amount > 0
        ]
        eligible_at_risk_count = len(at_risk_results)
        total_at_risk_value = sum(r.at_risk_amount for r in at_risk_results)

        # Recoverable (ground truth)
        gt_recoverable = [r for r in at_risk_results if r.ground_truth_recoverable is True]
        estimated_recoverable_value = sum(r.at_risk_amount for r in gt_recoverable) * Decimal("0.40")

        # Successful
        successful = [r for r in at_risk_results if r.recovery_succeeded]
        recovered_value = sum(r.recovered_amount for r in successful)

        # Rates
        recovery_rate_count = (
            Decimal(len(successful)) / Decimal(eligible_at_risk_count)
            if eligible_at_risk_count > 0
            else Decimal("0")
        )
        recovery_rate_value = (
            recovered_value / total_at_risk_value
            if total_at_risk_value > 0
            else Decimal("0")
        )

        # Retry stats
        retry_actions = [r for r in results if r.action_taken == "retry"]
        retry_successes = [r for r in retry_actions if r.recovery_succeeded]
        retry_success_rate = (
            Decimal(len(retry_successes)) / Decimal(len(retry_actions))
            if retry_actions
            else Decimal("0")
        )

        # Failed actions
        failed_actions = [r for r in at_risk_results if not r.recovery_succeeded and not r.action_blocked and r.action_taken not in ("none", "stop", "human_review")]
        action_failure_rate = (
            Decimal(len(failed_actions)) / Decimal(eligible_at_risk_count)
            if eligible_at_risk_count > 0
            else Decimal("0")
        )

        blocked = [r for r in results if r.action_blocked]
        human_review = [r for r in results if r.action_taken == "human_review"]
        contacts = [r for r in results if r.action_taken in CONTACT_ACTIONS]
        intervention_cost = sum(r.intervention_cost for r in results)
        net_recovery = recovered_value - intervention_cost

        duplicate_prevented = 0  # Would be tracked in full agent run

        # False positives — intervened but ground truth was not recoverable
        fp = [r for r in results if r.is_false_positive]

        # Classification metrics
        tp = sum(1 for r in results if r.is_true_positive)
        total_predicted_positive = sum(1 for r in results if r.predicted_recoverable is True)
        total_actual_positive = sum(1 for r in results if r.ground_truth_recoverable is True)
        total_actual_negative = sum(1 for r in results if r.ground_truth_recoverable is False)
        fn = sum(1 for r in results if r.is_false_negative)
        fp_count = sum(1 for r in results if r.is_false_positive)

        precision = (
            Decimal(tp) / Decimal(total_predicted_positive)
            if total_predicted_positive > 0
            else None
        )
        recall = (
            Decimal(tp) / Decimal(total_actual_positive)
            if total_actual_positive > 0
            else None
        )
        fpr = (
            Decimal(fp_count) / Decimal(total_actual_negative)
            if total_actual_negative > 0
            else None
        )

        # Category breakdown
        category_counts: Dict[str, Dict] = {}
        for r in results:
            cat = r.predicted_category or "unknown"
            if cat not in category_counts:
                category_counts[cat] = {"count": 0, "recovered": 0, "value": Decimal("0")}
            category_counts[cat]["count"] += 1
            if r.recovery_succeeded:
                category_counts[cat]["recovered"] += 1
                category_counts[cat]["value"] += r.recovered_amount

        # Convert Decimals to float for JSON
        results_by_category = {
            k: {
                "count": v["count"],
                "recovered": v["recovered"],
                "value": float(v["value"]),
            }
            for k, v in category_counts.items()
        }

        return {
            "total_transaction_count": total,
            "total_transaction_value": total_value,
            "eligible_at_risk_count": eligible_at_risk_count,
            "total_revenue_at_risk": total_at_risk_value,
            "estimated_recoverable_value": estimated_recoverable_value,
            "successful_recoveries": len(successful),
            "simulated_recovered_value": recovered_value,
            "recovery_rate_by_count": recovery_rate_count,
            "recovery_rate_by_value": recovery_rate_value,
            "retry_success_rate": retry_success_rate,
            "action_failure_rate": action_failure_rate,
            "blocked_action_count": len(blocked),
            "duplicate_prevented_count": duplicate_prevented,
            "human_review_count": len(human_review),
            "customer_contact_count": len(contacts),
            "estimated_intervention_cost": intervention_cost,
            "net_simulated_recovery_value": net_recovery,
            "false_positive_intervention_count": len(fp),
            "results_by_category": results_by_category,
            "precision": precision,
            "recall": recall,
            "false_positive_rate": fpr,
        }

    def _populate_run_metrics(
        self, run: EvaluationRun, metrics: Dict[str, Any]
    ) -> None:
        run.total_transaction_count = metrics["total_transaction_count"]
        run.total_transaction_value = metrics["total_transaction_value"]
        run.eligible_at_risk_count = metrics["eligible_at_risk_count"]
        run.total_revenue_at_risk = metrics["total_revenue_at_risk"]
        run.estimated_recoverable_value = metrics["estimated_recoverable_value"]
        run.successful_recoveries = metrics["successful_recoveries"]
        run.simulated_recovered_value = metrics["simulated_recovered_value"]
        run.recovery_rate_by_count = metrics["recovery_rate_by_count"]
        run.recovery_rate_by_value = metrics["recovery_rate_by_value"]
        run.retry_success_rate = metrics["retry_success_rate"]
        run.action_failure_rate = metrics["action_failure_rate"]
        run.blocked_action_count = metrics["blocked_action_count"]
        run.duplicate_prevented_count = metrics["duplicate_prevented_count"]
        run.human_review_count = metrics["human_review_count"]
        run.customer_contact_count = metrics["customer_contact_count"]
        run.estimated_intervention_cost = metrics["estimated_intervention_cost"]
        run.net_simulated_recovery_value = metrics["net_simulated_recovery_value"]
        run.false_positive_intervention_count = metrics["false_positive_intervention_count"]
        run.results_by_category = metrics["results_by_category"]
        run.precision = metrics["precision"]
        run.recall = metrics["recall"]
        run.false_positive_rate = metrics["false_positive_rate"]
