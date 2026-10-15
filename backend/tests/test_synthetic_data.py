"""
Tests for synthetic dataset generator.
"""
import pytest
from app.services.synthetic_data import generate_synthetic_dataset


class TestSyntheticDataGenerator:
    def test_generates_correct_count(self):
        dataset = generate_synthetic_dataset(count=50, seed=42)
        assert dataset["metadata"]["count"] == 50

    def test_reproducible_with_same_seed(self):
        """Same seed produces same structure, amounts, and failure categories."""
        d1 = generate_synthetic_dataset(count=50, seed=42)
        d2 = generate_synthetic_dataset(count=50, seed=42)
        # Structure and counts are reproducible
        assert d1["metadata"]["count"] == d2["metadata"]["count"]
        assert d1["metadata"]["label_distribution"] == d2["metadata"]["label_distribution"]
        # Amount of first record is reproducible (random.uniform is seeded)
        assert d1["records"][0]["amount"] == d2["records"][0]["amount"]
        # Failure categories follow same distribution
        cats1 = [r.get("failure_category") for r in d1["records"]]
        cats2 = [r.get("failure_category") for r in d2["records"]]
        assert cats1 == cats2

    def test_different_seed_produces_different_data(self):
        d1 = generate_synthetic_dataset(count=50, seed=42)
        d2 = generate_synthetic_dataset(count=50, seed=99)
        assert d1["records"][0]["id"] != d2["records"][0]["id"]

    def test_all_required_fields_present(self):
        dataset = generate_synthetic_dataset(count=10, seed=42)
        required = ["id", "external_id", "customer_ref", "amount", "currency",
                    "transaction_type", "status", "is_synthetic"]
        for record in dataset["records"]:
            for field in required:
                assert field in record, f"Missing field: {field}"

    def test_contains_duplicate_rows(self):
        dataset = generate_synthetic_dataset(count=50, seed=42)
        assert len(dataset["duplicate_records"]) >= 2

    def test_contains_invalid_rows(self):
        dataset = generate_synthetic_dataset(count=50, seed=42)
        assert len(dataset["invalid_records"]) >= 2

    def test_all_synthetic_flag_set(self):
        dataset = generate_synthetic_dataset(count=20, seed=42)
        assert all(r["is_synthetic"] for r in dataset["records"])

    def test_ground_truth_labels_present(self):
        dataset = generate_synthetic_dataset(count=50, seed=42)
        labeled = [r for r in dataset["records"]
                   if r.get("synthetic_ground_truth_recoverable") is not None]
        assert len(labeled) > 0

    def test_scenario_coverage(self):
        """Verify all required scenarios are present."""
        dataset = generate_synthetic_dataset(count=100, seed=42)
        outcomes = {r.get("synthetic_recovery_outcome") for r in dataset["records"]}
        statuses = {r["status"] for r in dataset["records"]}
        types = {r["transaction_type"] for r in dataset["records"]}

        # Must have multiple transaction types
        assert "payment" in types
        assert "checkout" in types or "subscription" in types or "invoice" in types

        # Must have multiple statuses
        assert "failed" in statuses
        assert "success" in statuses

        # Must have ground truth outcomes
        assert outcomes - {None}  # At least some non-None outcomes

    def test_fraud_cases_non_recoverable(self):
        dataset = generate_synthetic_dataset(count=100, seed=42)
        fraud_cases = [r for r in dataset["records"] if r.get("failure_category") == "fraud"]
        assert len(fraud_cases) > 0
        for case in fraud_cases:
            assert case["synthetic_ground_truth_recoverable"] == False

    def test_temp_failure_cases_recoverable(self):
        dataset = generate_synthetic_dataset(count=100, seed=42)
        temp_cases = [r for r in dataset["records"]
                      if r.get("failure_category") == "temp_failure"
                      and r.get("recovery_status") != "blocked"]
        assert len(temp_cases) > 0
        recoverable = [c for c in temp_cases if c["synthetic_ground_truth_recoverable"] == True]
        assert len(recoverable) > 0

    def test_metadata_structure(self):
        dataset = generate_synthetic_dataset(count=50, seed=42)
        meta = dataset["metadata"]
        assert "seed" in meta
        assert "count" in meta
        assert "label_distribution" in meta
        assert meta["seed"] == 42
