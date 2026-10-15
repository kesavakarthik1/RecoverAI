"""
Tests for risk scoring service.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from app.services.risk_scoring import calculate_risk_score


class TestRiskScoring:
    def test_fraud_gives_high_score(self):
        result = calculate_risk_score(
            failure_category="fraud",
            retry_count=0,
            amount=Decimal("5000"),
            failure_timestamp=None,
            transaction_type="payment",
        )
        assert float(result["risk_score"]) >= 90
        assert result["recoverability"] == "non_recoverable"

    def test_temp_failure_is_recoverable(self):
        result = calculate_risk_score(
            failure_category="temp_failure",
            retry_count=0,
            amount=Decimal("5000"),
            failure_timestamp=None,
            transaction_type="payment",
        )
        assert result["recoverability"] == "recoverable"

    def test_invalid_details_is_non_recoverable(self):
        result = calculate_risk_score(
            failure_category="invalid_details",
            retry_count=1,
            amount=Decimal("5000"),
            failure_timestamp=None,
            transaction_type="payment",
        )
        assert result["recoverability"] == "non_recoverable"

    def test_unknown_category_requires_review(self):
        result = calculate_risk_score(
            failure_category="unknown",
            retry_count=0,
            amount=Decimal("5000"),
            failure_timestamp=None,
            transaction_type="payment",
        )
        assert result["recoverability"] == "requires_review"
        assert result["requires_human_review"]

    def test_high_amount_increases_score(self):
        low = calculate_risk_score(
            failure_category="temp_failure", retry_count=0,
            amount=Decimal("500"), failure_timestamp=None, transaction_type="payment"
        )
        high = calculate_risk_score(
            failure_category="temp_failure", retry_count=0,
            amount=Decimal("100000"), failure_timestamp=None, transaction_type="payment"
        )
        assert float(high["risk_score"]) > float(low["risk_score"])

    def test_max_retries_increases_score(self):
        low_retry = calculate_risk_score(
            failure_category="temp_failure", retry_count=0,
            amount=Decimal("5000"), failure_timestamp=None, transaction_type="payment"
        )
        high_retry = calculate_risk_score(
            failure_category="temp_failure", retry_count=3,
            amount=Decimal("5000"), failure_timestamp=None, transaction_type="payment"
        )
        assert float(high_retry["risk_score"]) > float(low_retry["risk_score"])

    def test_old_failure_increases_score(self):
        fresh = calculate_risk_score(
            failure_category="temp_failure", retry_count=0,
            amount=Decimal("5000"),
            failure_timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
            transaction_type="payment"
        )
        old = calculate_risk_score(
            failure_category="temp_failure", retry_count=0,
            amount=Decimal("5000"),
            failure_timestamp=datetime.now(timezone.utc) - timedelta(days=5),
            transaction_type="payment"
        )
        assert float(old["risk_score"]) > float(fresh["risk_score"])

    def test_priority_levels(self):
        fraud_result = calculate_risk_score(
            failure_category="fraud", retry_count=0,
            amount=Decimal("50000"), failure_timestamp=None, transaction_type="payment"
        )
        assert fraud_result["priority"] == "critical"

        temp_result = calculate_risk_score(
            failure_category="temp_failure", retry_count=0,
            amount=Decimal("100"), failure_timestamp=None, transaction_type="payment"
        )
        assert temp_result["priority"] in ("low", "medium")

    def test_cancelled_subscription_low_score(self):
        result = calculate_risk_score(
            failure_category="invalid_details", retry_count=0,
            amount=Decimal("5000"), failure_timestamp=None,
            transaction_type="subscription",
            description="cancelled_subscription"
        )
        assert result["recoverability"] == "non_recoverable"

    def test_disputed_invoice_requires_review(self):
        result = calculate_risk_score(
            failure_category="unknown", retry_count=0,
            amount=Decimal("5000"), failure_timestamp=None,
            transaction_type="invoice",
            description="disputed_invoice"
        )
        assert result["requires_human_review"]

    def test_score_bounded_0_to_100(self):
        for cat in ["fraud", "temp_failure", "unknown", "auth_required"]:
            result = calculate_risk_score(
                failure_category=cat, retry_count=5,
                amount=Decimal("999999"), failure_timestamp=None,
                transaction_type="payment"
            )
            assert 0 <= float(result["risk_score"]) <= 100

    def test_risk_factors_list_not_empty(self):
        result = calculate_risk_score(
            failure_category="temp_failure", retry_count=1,
            amount=Decimal("5000"), failure_timestamp=None, transaction_type="payment"
        )
        assert len(result["risk_factors"]) > 0
