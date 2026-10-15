"""
Deterministic Policy Engine.

This engine is AUTHORITATIVE — even if an AI recommends an action,
the policy engine can block it. LLM output never overrides a blocked action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional


@dataclass
class PolicyContext:
    """Input context for a policy evaluation."""
    transaction_id: str
    merchant_id: str
    transaction_type: str
    failure_category: Optional[str]
    retry_count: int
    amount: Decimal
    currency: str
    recovery_status: str
    recoverability: str
    action_count: int

    # Customer state
    customer_opted_out: bool = False
    customer_email_eligible: bool = True
    customer_reminder_count_7d: int = 0

    # Subscription / invoice state
    subscription_cancelled: bool = False
    invoice_disputed: bool = False

    # Timing
    last_retry_at: Optional[datetime] = None
    last_action_at: Optional[datetime] = None
    failure_timestamp: Optional[datetime] = None

    # Batch limits
    batch_action_count: int = 0

    # Description flags
    description: Optional[str] = None


@dataclass
class PolicyResult:
    """Output of a policy evaluation."""
    allowed: bool
    rule_id: str
    reason: str
    requires_approval: bool = False
    remaining_retry_budget: int = 0
    remaining_communication_budget: int = 0
    blocking_rules: List[str] = field(default_factory=list)


@dataclass
class PolicyConfig:
    """Policy configuration loaded from DB or defaults."""
    max_retry_attempts: int = 3
    min_retry_delay_hours: int = 24
    max_recovery_actions_per_txn: int = 5
    max_reminders_per_customer_per_week: int = 2
    require_communication_consent: bool = True
    approval_threshold_amount: Decimal = Decimal("50000")
    retryable_failure_categories: List[str] = field(
        default_factory=lambda: ["temp_failure"]
    )
    non_retryable_categories: List[str] = field(
        default_factory=lambda: ["fraud", "invalid_details"]
    )
    batch_max_actions: int = 500


class PolicyEngine:
    """
    Enforces all recovery policy rules.
    Evaluation is purely deterministic — no LLM involvement.
    """

    def __init__(self, config: Optional[PolicyConfig] = None) -> None:
        self.config = config or PolicyConfig()

    def evaluate(self, ctx: PolicyContext, proposed_action: str) -> PolicyResult:
        """
        Evaluate whether a proposed action is allowed.

        Stopping rules are checked in order. The first matching blocking
        rule halts evaluation and returns a BLOCKED result.
        """
        cfg = self.config

        # ── HARD STOPS (always block) ─────────────────────────────────────────

        # 1. Case already closed
        if ctx.recovery_status in ("closed", "recovered"):
            return PolicyResult(
                allowed=False,
                rule_id="STOP_001",
                reason="Recovery case is already closed or successfully recovered.",
                blocking_rules=["STOP_001"],
            )

        # 2. Confirmed payment (should never reach here, but safety catch)
        if ctx.recovery_status == "recovered":
            return PolicyResult(
                allowed=False,
                rule_id="STOP_002",
                reason="Payment already confirmed as recovered.",
                blocking_rules=["STOP_002"],
            )

        # 3. Fraud / security restriction — no automated action
        if ctx.failure_category == "fraud":
            return PolicyResult(
                allowed=False,
                rule_id="STOP_003",
                reason="Fraud or security restriction: no automated recovery permitted.",
                blocking_rules=["STOP_003"],
            )

        # 4. Non-retryable failure category
        if ctx.failure_category in cfg.non_retryable_categories:
            if proposed_action == "retry":
                return PolicyResult(
                    allowed=False,
                    rule_id="STOP_004",
                    reason=f"Failure category '{ctx.failure_category}' is non-retryable.",
                    blocking_rules=["STOP_004"],
                )

        # 5. Cancelled subscription
        if ctx.subscription_cancelled or (
            ctx.description and "cancelled_subscription" in ctx.description.lower()
        ):
            return PolicyResult(
                allowed=False,
                rule_id="STOP_005",
                reason="Subscription is cancelled: recovery is not permitted.",
                blocking_rules=["STOP_005"],
            )

        # 6. Disputed invoice — escalate to human review only
        if ctx.invoice_disputed or (
            ctx.description and "disputed_invoice" in ctx.description.lower()
        ):
            if proposed_action not in ("human_review", "stop"):
                return PolicyResult(
                    allowed=False,
                    rule_id="STOP_006",
                    reason="Invoice is disputed: must be escalated to human review.",
                    blocking_rules=["STOP_006"],
                )

        # 7. Customer opted out of communications
        if ctx.customer_opted_out or (
            ctx.description and "opted_out_customer" in ctx.description.lower()
        ):
            if proposed_action in ("send_reminder", "send_contact"):
                return PolicyResult(
                    allowed=False,
                    rule_id="STOP_007",
                    reason="Customer has opted out of communications.",
                    blocking_rules=["STOP_007"],
                )

        # ── RETRY LIMITS ──────────────────────────────────────────────────────

        # 8. Max retry count reached
        if proposed_action == "retry":
            if ctx.retry_count >= cfg.max_retry_attempts:
                return PolicyResult(
                    allowed=False,
                    rule_id="RETRY_001",
                    reason=f"Maximum retry attempts ({cfg.max_retry_attempts}) reached.",
                    remaining_retry_budget=0,
                    blocking_rules=["RETRY_001"],
                )

            # 9. Minimum delay between retries
            if ctx.last_retry_at:
                now = datetime.now(timezone.utc)
                last_retry = ctx.last_retry_at
                if last_retry.tzinfo is None:
                    last_retry = last_retry.replace(tzinfo=timezone.utc)
                hours_since = (now - last_retry).total_seconds() / 3600
                if hours_since < cfg.min_retry_delay_hours:
                    return PolicyResult(
                        allowed=False,
                        rule_id="RETRY_002",
                        reason=(
                            f"Minimum retry delay not elapsed. "
                            f"Wait {cfg.min_retry_delay_hours - int(hours_since)}h more."
                        ),
                        remaining_retry_budget=cfg.max_retry_attempts - ctx.retry_count,
                        blocking_rules=["RETRY_002"],
                    )

            # 10. Failure category not retryable
            if ctx.failure_category and ctx.failure_category not in cfg.retryable_failure_categories:
                return PolicyResult(
                    allowed=False,
                    rule_id="RETRY_003",
                    reason=f"Failure category '{ctx.failure_category}' is not in retryable list.",
                    blocking_rules=["RETRY_003"],
                )

        # ── COMMUNICATION LIMITS ─────────────────────────────────────────────

        # 11. Communication limit
        if proposed_action in ("send_reminder", "send_contact"):
            if not ctx.customer_email_eligible and not ctx.customer_opted_out:
                pass  # OK, just no email channel
            if ctx.customer_reminder_count_7d >= cfg.max_reminders_per_customer_per_week:
                return PolicyResult(
                    allowed=False,
                    rule_id="COMM_001",
                    reason=(
                        f"Customer communication limit reached: "
                        f"{ctx.customer_reminder_count_7d}/{cfg.max_reminders_per_customer_per_week} "
                        "reminders in the last 7 days."
                    ),
                    remaining_communication_budget=0,
                    blocking_rules=["COMM_001"],
                )

        # ── ACTION BUDGET ─────────────────────────────────────────────────────

        # 12. Max recovery actions per transaction
        if ctx.action_count >= cfg.max_recovery_actions_per_txn:
            return PolicyResult(
                allowed=False,
                rule_id="ACT_001",
                reason=f"Maximum recovery actions per transaction ({cfg.max_recovery_actions_per_txn}) reached.",
                blocking_rules=["ACT_001"],
            )

        # 13. Batch action limit
        if ctx.batch_action_count >= cfg.batch_max_actions:
            return PolicyResult(
                allowed=False,
                rule_id="ACT_002",
                reason=f"Batch action limit ({cfg.batch_max_actions}) reached.",
                blocking_rules=["ACT_002"],
            )

        # ── APPROVAL THRESHOLDS ───────────────────────────────────────────────

        requires_approval = ctx.amount >= cfg.approval_threshold_amount

        # ── ALLOWED ───────────────────────────────────────────────────────────
        remaining_retry_budget = max(0, cfg.max_retry_attempts - ctx.retry_count)
        remaining_comm_budget = max(
            0, cfg.max_reminders_per_customer_per_week - ctx.customer_reminder_count_7d
        )

        return PolicyResult(
            allowed=True,
            rule_id="ALLOWED",
            reason="All policy checks passed.",
            requires_approval=requires_approval,
            remaining_retry_budget=remaining_retry_budget,
            remaining_communication_budget=remaining_comm_budget,
        )
