"""
Tests for payment provider adapters.
"""
import pytest
from decimal import Decimal

from app.integrations.payment_provider import SimulationProvider, get_payment_provider


class TestSimulationProvider:
    @pytest.fixture
    def provider(self):
        return SimulationProvider(seed=42)

    @pytest.mark.asyncio
    async def test_execute_action_returns_dict(self, provider):
        result = await provider.execute_action(
            action_type="retry",
            transaction_id="txn-001",
            amount=Decimal("5000"),
            currency="INR",
            metadata={"failure_category": "temp_failure"},
        )
        assert isinstance(result, dict)
        assert "success" in result
        assert result["simulated"] is True

    @pytest.mark.asyncio
    async def test_deterministic_outcome_same_inputs(self, provider):
        r1 = await provider.execute_action(
            action_type="retry", transaction_id="fixed-id",
            amount=Decimal("5000"), currency="INR",
            metadata={"failure_category": "temp_failure"},
        )
        r2 = await provider.execute_action(
            action_type="retry", transaction_id="fixed-id",
            amount=Decimal("5000"), currency="INR",
            metadata={"failure_category": "temp_failure"},
        )
        assert r1["success"] == r2["success"]

    @pytest.mark.asyncio
    async def test_fraud_action_has_low_success_rate(self, provider):
        results = []
        for i in range(20):
            r = await provider.execute_action(
                action_type="retry",
                transaction_id=f"fraud-txn-{i}",
                amount=Decimal("5000"),
                currency="INR",
                metadata={"failure_category": "fraud"},
            )
            results.append(r["success"])
        # fraud should rarely succeed for retry
        assert sum(results) / len(results) < 0.5

    @pytest.mark.asyncio
    async def test_human_review_always_succeeds(self, provider):
        result = await provider.execute_action(
            action_type="human_review",
            transaction_id="txn-001",
            amount=Decimal("5000"),
            currency="INR",
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_stop_action_always_succeeds(self, provider):
        result = await provider.execute_action(
            action_type="stop",
            transaction_id="txn-001",
            amount=Decimal("5000"),
            currency="INR",
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_provider_name(self, provider):
        assert provider.provider_name == "simulation"
        assert provider.is_live is False

    @pytest.mark.asyncio
    async def test_get_payment_status(self, provider):
        result = await provider.get_payment_status("txn-001")
        assert "provider" in result
        assert result["simulated"] is True


class TestProviderFactory:
    def test_simulation_provider_is_default(self):
        provider = get_payment_provider()
        assert provider.provider_name == "simulation"
        assert not provider.is_live
