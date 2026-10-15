"""
Tests for the deterministic Policy Engine.
Covers: stopping rules, retry limits, communication limits, fraud blocks,
        cancelled subscriptions, opted-out customers, disputed invoices,
        approval thresholds, and batch limits.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from app.policies.policy_engine import PolicyContext, PolicyConfig, PolicyEngine


def make_ctx(**kwargs) -> PolicyContext:
    defaults = dict(
        transaction_id="txn-001",
        merchant_id="merch-001",
        transaction_type="payment",
        failure_category="temp_failure",
        retry_count=0,
        amount=Decimal("5000"),
        currency="INR",
        recovery_status="pending",
        recoverability="recoverable",
        action_count=0,
        batch_action_count=0,
    )
    defaults.update(kwargs)
    return PolicyContext(**defaults)


class TestPolicyEngine:
    def setup_method(self):
        self.engine = PolicyEngine()

    # ── Stopping rules ────────────────────────────────────────────────────────

    def test_already_closed_case_is_blocked(self):
        ctx = make_ctx(recovery_status="closed")
        result = self.engine.evaluate(ctx, "retry")
        assert not result.allowed
        assert result.rule_id == "STOP_001"

    def test_already_recovered_is_blocked(self):
        ctx = make_ctx(recovery_status="recovered")
        result = self.engine.evaluate(ctx, "retry")
        assert not result.allowed

    def test_fraud_always_blocked(self):
        ctx = make_ctx(failure_category="fraud")
        result = self.engine.evaluate(ctx, "retry")
        assert not result.allowed
        assert result.rule_id == "STOP_003"

    def test_fraud_blocks_all_actions(self):
        ctx = make_ctx(failure_category="fraud")
        for action in ["retry", "send_reminder", "escalate"]:
            result = self.engine.evaluate(ctx, action)
            assert not result.allowed

    def test_cancelled_subscription_blocked(self):
        ctx = make_ctx(description="cancelled_subscription")
        result = self.engine.evaluate(ctx, "retry")
        assert not result.allowed
        assert result.rule_id == "STOP_005"

    def test_disputed_invoice_allows_only_human_review(self):
        ctx = make_ctx(description="disputed_invoice")
        result_review = self.engine.evaluate(ctx, "human_review")
        assert result_review.allowed

        result_retry = self.engine.evaluate(ctx, "retry")
        assert not result_retry.allowed
        assert result_retry.rule_id == "STOP_006"

    def test_opted_out_customer_blocks_communication(self):
        ctx = make_ctx(description="opted_out_customer")
        result = self.engine.evaluate(ctx, "send_reminder")
        assert not result.allowed
        assert result.rule_id == "STOP_007"

    def test_opted_out_allows_retry(self):
        ctx = make_ctx(
            description="opted_out_customer",
            failure_category="temp_failure",
        )
        result = self.engine.evaluate(ctx, "retry")
        assert result.allowed

    # ── Retry limits ─────────────────────────────────────────────────────────

    def test_max_retry_count_blocks(self):
        ctx = make_ctx(retry_count=3)
        result = self.engine.evaluate(ctx, "retry")
        assert not result.allowed
        assert result.rule_id == "RETRY_001"

    def test_retry_within_limit_allowed(self):
        ctx = make_ctx(retry_count=2, failure_category="temp_failure")
        result = self.engine.evaluate(ctx, "retry")
        assert result.allowed

    def test_retry_delay_not_elapsed_blocked(self):
        recent = datetime.now(timezone.utc) - timedelta(hours=2)
        ctx = make_ctx(
            failure_category="temp_failure",
            last_retry_at=recent,
            retry_count=1,
        )
        result = self.engine.evaluate(ctx, "retry")
        assert not result.allowed
        assert result.rule_id == "RETRY_002"

    def test_retry_delay_elapsed_allowed(self):
        old = datetime.now(timezone.utc) - timedelta(hours=48)
        ctx = make_ctx(
            failure_category="temp_failure",
            last_retry_at=old,
            retry_count=1,
        )
        result = self.engine.evaluate(ctx, "retry")
        assert result.allowed

    def test_non_retryable_category_blocks_retry(self):
        for cat in ["insufficient_funds", "invalid_details"]:
            ctx = make_ctx(failure_category=cat, recoverability="non_recoverable")
            result = self.engine.evaluate(ctx, "retry")
            assert not result.allowed, f"Expected block for {cat}"

    # ── Communication limits ──────────────────────────────────────────────────

    def test_communication_limit_blocks_reminder(self):
        ctx = make_ctx(customer_reminder_count_7d=2)
        result = self.engine.evaluate(ctx, "send_reminder")
        assert not result.allowed
        assert result.rule_id == "COMM_001"

    def test_communication_within_limit_allowed(self):
        ctx = make_ctx(customer_reminder_count_7d=1)
        result = self.engine.evaluate(ctx, "send_reminder")
        assert result.allowed

    # ── Action budget ─────────────────────────────────────────────────────────

    def test_max_actions_per_transaction_blocks(self):
        ctx = make_ctx(action_count=5)
        result = self.engine.evaluate(ctx, "retry")
        assert not result.allowed
        assert result.rule_id == "ACT_001"

    def test_batch_action_limit_blocks(self):
        ctx = make_ctx(batch_action_count=500)
        result = self.engine.evaluate(ctx, "retry")
        assert not result.allowed
        assert result.rule_id == "ACT_002"

    # ── Approval thresholds ───────────────────────────────────────────────────

    def test_high_value_requires_approval(self):
        ctx = make_ctx(
            amount=Decimal("100000"),
            failure_category="temp_failure",
        )
        result = self.engine.evaluate(ctx, "retry")
        assert result.allowed
        assert result.requires_approval

    def test_low_value_no_approval_needed(self):
        ctx = make_ctx(
            amount=Decimal("1000"),
            failure_category="temp_failure",
        )
        result = self.engine.evaluate(ctx, "retry")
        assert result.allowed
        assert not result.requires_approval

    # ── Budget remaining ──────────────────────────────────────────────────────

    def test_remaining_retry_budget_returned(self):
        ctx = make_ctx(retry_count=1, failure_category="temp_failure")
        result = self.engine.evaluate(ctx, "retry")
        assert result.allowed
        assert result.remaining_retry_budget == 2  # 3 max - 1 used

    def test_remaining_communication_budget_returned(self):
        ctx = make_ctx(customer_reminder_count_7d=1)
        result = self.engine.evaluate(ctx, "send_reminder")
        assert result.allowed
        assert result.remaining_communication_budget == 1

    # ── Custom config ─────────────────────────────────────────────────────────

    def test_custom_max_retries(self):
        config = PolicyConfig(max_retry_attempts=5)
        engine = PolicyEngine(config)
        ctx = make_ctx(retry_count=4, failure_category="temp_failure")
        result = engine.evaluate(ctx, "retry")
        assert result.allowed

        ctx5 = make_ctx(retry_count=5, failure_category="temp_failure")
        result5 = engine.evaluate(ctx5, "retry")
        assert not result5.allowed
