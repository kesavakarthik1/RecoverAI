"""
Tests for AI provider (rule-based and fallback behavior).
"""
import pytest
import pytest_asyncio
from decimal import Decimal

from app.agent.ai_provider import RuleBasedProvider, get_ai_provider


class TestRuleBasedProvider:
    @pytest.fixture
    def provider(self):
        return RuleBasedProvider()

    @pytest.mark.asyncio
    async def test_temp_failure_recommends_retry(self, provider):
        ctx = {
            "transaction_type": "payment",
            "failure_category": "temp_failure",
            "retry_count": 0,
            "max_retries": 3,
            "amount": 5000.0,
            "currency": "INR",
            "recoverability": "recoverable",
        }
        rec = await provider.get_recommendation(ctx)
        assert rec.recommended_action == "retry"
        assert rec.source == "rule_based"

    @pytest.mark.asyncio
    async def test_fraud_recommends_stop(self, provider):
        ctx = {
            "transaction_type": "payment",
            "failure_category": "fraud",
            "retry_count": 0,
            "max_retries": 3,
            "amount": 5000.0,
            "currency": "INR",
            "recoverability": "non_recoverable",
        }
        rec = await provider.get_recommendation(ctx)
        assert rec.recommended_action == "stop"

    @pytest.mark.asyncio
    async def test_auth_required_recommends_request_auth(self, provider):
        ctx = {
            "transaction_type": "payment",
            "failure_category": "auth_required",
            "retry_count": 0,
            "max_retries": 3,
            "amount": 5000.0,
            "currency": "INR",
            "recoverability": "recoverable",
        }
        rec = await provider.get_recommendation(ctx)
        assert rec.recommended_action == "request_auth"

    @pytest.mark.asyncio
    async def test_unknown_recommends_human_review(self, provider):
        ctx = {
            "transaction_type": "payment",
            "failure_category": "unknown",
            "retry_count": 0,
            "max_retries": 3,
            "amount": 5000.0,
            "currency": "INR",
            "recoverability": "requires_review",
        }
        rec = await provider.get_recommendation(ctx)
        assert rec.recommended_action == "human_review"

    @pytest.mark.asyncio
    async def test_cancelled_subscription_recommends_stop(self, provider):
        ctx = {
            "transaction_type": "subscription",
            "failure_category": "temp_failure",
            "retry_count": 0,
            "max_retries": 3,
            "amount": 5000.0,
            "currency": "INR",
            "recoverability": "recoverable",
            "description": "cancelled_subscription",
        }
        rec = await provider.get_recommendation(ctx)
        assert rec.recommended_action == "stop"

    @pytest.mark.asyncio
    async def test_confidence_range_valid(self, provider):
        ctx = {
            "transaction_type": "payment",
            "failure_category": "temp_failure",
            "retry_count": 0,
            "max_retries": 3,
            "amount": 5000.0,
            "currency": "INR",
        }
        rec = await provider.get_recommendation(ctx)
        assert 0.0 <= rec.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_high_value_requires_approval(self, provider):
        ctx = {
            "transaction_type": "payment",
            "failure_category": "temp_failure",
            "retry_count": 0,
            "max_retries": 3,
            "amount": 100000.0,
            "currency": "INR",
        }
        rec = await provider.get_recommendation(ctx)
        assert rec.requires_human_approval

    @pytest.mark.asyncio
    async def test_reminder_draft_generated(self, provider):
        ctx = {
            "transaction_type": "checkout",
            "amount": 5000.0,
            "currency": "INR",
        }
        draft = await provider.generate_reminder_draft(ctx)
        assert isinstance(draft, str)
        assert len(draft) > 10

    @pytest.mark.asyncio
    async def test_batch_summary_generated(self, provider):
        summary = await provider.summarise_batch_risk({
            "total_revenue_at_risk": 100000,
            "estimated_recoverable_value": 40000,
            "eligible_at_risk_count": 20,
        })
        assert isinstance(summary, str)
        assert len(summary) > 10


class TestAIProviderFactory:
    def test_rule_based_provider_returned_without_key(self):
        provider = get_ai_provider()
        assert isinstance(provider, RuleBasedProvider)
