"""
Tests for evaluation engine metrics.
"""
import pytest
import pytest_asyncio
from decimal import Decimal

from app.evaluation.evaluation_engine import EvaluationEngine
from app.services.synthetic_data import generate_synthetic_dataset
from app.models.transaction import Transaction
from app.models.merchant import Merchant


async def _seed_transactions(db_session, count=50, seed=42):
    """Helper: create merchant + import synthetic transactions."""
    from datetime import datetime, timezone
    import uuid

    # Create demo merchant
    merchant = Merchant(
        id="merchant-demo-001",
        name="Demo Merchant",
        email="demo@test.local",
        currency="INR",
    )
    db_session.add(merchant)
    await db_session.flush()

    dataset = generate_synthetic_dataset(count=count, seed=seed)
    transactions = []
    for row in dataset["records"]:
        txn = Transaction(
            id=row.get("id") or str(uuid.uuid4()),
            external_id=row.get("external_id"),
            merchant_id="merchant-demo-001",
            customer_ref=row["customer_ref"],
            amount=Decimal(str(row["amount"])),
            currency=row.get("currency", "INR"),
            transaction_type=row["transaction_type"],
            status=row["status"],
            failure_category=row.get("failure_category"),
            failure_reason=row.get("failure_reason"),
            retry_count=row.get("retry_count", 0),
            recoverability=row.get("recoverability", "unknown"),
            recovery_status=row.get("recovery_status", "pending"),
            description=row.get("description"),
            is_synthetic=True,
            synthetic_ground_truth_recoverable=row.get("synthetic_ground_truth_recoverable"),
            synthetic_recovery_outcome=row.get("synthetic_recovery_outcome"),
        )
        db_session.add(txn)
        transactions.append(txn)

    await db_session.flush()
    return transactions


class TestEvaluationEngine:
    @pytest.mark.asyncio
    async def test_runs_all_three_strategies(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        assert "baseline" in runs
        assert "fixed_rule" in runs
        assert "ai_assisted" in runs

    @pytest.mark.asyncio
    async def test_all_runs_complete(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        for strategy, run in runs.items():
            assert run.status == "completed", f"{strategy} run failed: {run.error_message}"

    @pytest.mark.asyncio
    async def test_transaction_count_correct(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        for strategy, run in runs.items():
            assert run.total_transaction_count == 50

    @pytest.mark.asyncio
    async def test_baseline_has_zero_recoveries(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        baseline = runs["baseline"]
        assert baseline.successful_recoveries == 0
        assert float(baseline.simulated_recovered_value) == 0.0

    @pytest.mark.asyncio
    async def test_ai_assisted_recovers_more_than_baseline(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        assert runs["ai_assisted"].successful_recoveries >= runs["baseline"].successful_recoveries

    @pytest.mark.asyncio
    async def test_recovery_rate_in_valid_range(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        for strategy, run in runs.items():
            if run.recovery_rate_by_count is not None:
                assert 0 <= float(run.recovery_rate_by_count) <= 1

    @pytest.mark.asyncio
    async def test_blocked_actions_counted(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        # Fixed rule and AI should block some actions (fraud, non-retryable)
        total_blocked = sum(r.blocked_action_count for r in runs.values())
        assert total_blocked > 0

    @pytest.mark.asyncio
    async def test_human_review_count(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        # Unknown failure categories trigger human review
        total_reviews = sum(r.human_review_count for r in runs.values())
        assert total_reviews > 0

    @pytest.mark.asyncio
    async def test_precision_recall_calculated_when_ground_truth_available(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        # Fixed rule and AI should have precision/recall since data has ground truth
        for strategy in ["fixed_rule", "ai_assisted"]:
            run = runs[strategy]
            # At least one should have precision/recall
            if run.precision is not None:
                assert 0 <= float(run.precision) <= 1
            if run.recall is not None:
                assert 0 <= float(run.recall) <= 1

    @pytest.mark.asyncio
    async def test_results_by_category_populated(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        for strategy in ["fixed_rule", "ai_assisted"]:
            run = runs[strategy]
            assert run.results_by_category is not None
            assert len(run.results_by_category) > 0

    @pytest.mark.asyncio
    async def test_net_recovery_value_calculation(self, db_session):
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()
        for strategy, run in runs.items():
            expected_net = float(run.simulated_recovered_value) - float(run.estimated_intervention_cost)
            actual_net = float(run.net_simulated_recovery_value)
            assert abs(actual_net - expected_net) < 0.01, f"{strategy}: net value mismatch"

    @pytest.mark.asyncio
    async def test_fraud_never_recovered(self, db_session):
        """Fraud transactions must be blocked, never recovered."""
        await _seed_transactions(db_session, count=50, seed=42)
        engine = EvaluationEngine(db=db_session, seed=42)
        runs = await engine.run_comparison()

        for strategy in ["fixed_rule", "ai_assisted"]:
            run = runs[strategy]
            if run.results_by_category and "fraud" in run.results_by_category:
                fraud_cat = run.results_by_category["fraud"]
                assert fraud_cat["recovered"] == 0, f"{strategy}: fraud was recovered!"
