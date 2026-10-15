"""
Risk Scoring Service.
Calculates a deterministic risk score (0-100) for a transaction
based on failure category, retry count, amount, and timing.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


# Risk weights per failure category
CATEGORY_BASE_SCORES = {
    "temp_failure": 40,
    "auth_required": 35,
    "insufficient_funds": 65,
    "invalid_details": 75,
    "fraud": 95,
    "unknown": 55,
}

RECOVERABILITY_MAP = {
    "temp_failure": "recoverable",
    "auth_required": "recoverable",
    "insufficient_funds": "non_recoverable",
    "invalid_details": "non_recoverable",
    "fraud": "non_recoverable",
    "unknown": "requires_review",
}


def calculate_risk_score(
    *,
    failure_category: Optional[str],
    retry_count: int,
    amount: Decimal,
    failure_timestamp: Optional[datetime],
    transaction_type: str,
    description: Optional[str] = None,
    max_retries: int = 3,
) -> dict:
    """
    Calculate risk score and recoverability classification.

    Returns:
        {
          "risk_score": Decimal,
          "recoverability": str,
          "priority": str,
          "requires_human_review": bool,
          "risk_factors": list[str],
        }
    """
    risk_factors = []

    # Base score from failure category
    cat = (failure_category or "unknown").lower()
    base = CATEGORY_BASE_SCORES.get(cat, 55)
    risk_factors.append(f"failure_category={cat} base={base}")

    # Amount factor — higher amounts increase risk priority
    if amount >= 50000:
        base = min(100, base + 10)
        risk_factors.append("high_value_transaction +10")
    elif amount >= 10000:
        base = min(100, base + 5)
        risk_factors.append("medium_value_transaction +5")

    # Retry factor — more retries = higher risk of unrecoverability
    if retry_count >= max_retries:
        base = min(100, base + 15)
        risk_factors.append(f"retry_limit_reached ({retry_count}/{max_retries}) +15")
    elif retry_count > 0:
        base = min(100, base + retry_count * 3)
        risk_factors.append(f"previous_retries={retry_count} +{retry_count * 3}")

    # Time factor — older failures are harder to recover
    if failure_timestamp:
        now = datetime.now(timezone.utc)
        if failure_timestamp.tzinfo is None:
            failure_timestamp = failure_timestamp.replace(tzinfo=timezone.utc)
        hours_old = (now - failure_timestamp).total_seconds() / 3600
        if hours_old > 72:
            base = min(100, base + 10)
            risk_factors.append(f"failure_aged_{int(hours_old)}h +10")
        elif hours_old > 24:
            base = min(100, base + 5)
            risk_factors.append(f"failure_aged_{int(hours_old)}h +5")

    # Subscription type has higher urgency
    if transaction_type == "subscription":
        base = min(100, base + 5)
        risk_factors.append("subscription_type +5")

    # Description flags
    if description:
        desc_lower = description.lower()
        if "cancelled_subscription" in desc_lower:
            base = 20  # Low — can't recover
            risk_factors.append("cancelled_subscription override=20")
        elif "disputed" in desc_lower:
            base = min(100, base + 15)
            risk_factors.append("disputed +15")
        elif "opted_out" in desc_lower:
            base = min(100, base + 5)
            risk_factors.append("opted_out +5")

    # Determine recoverability
    recoverability = RECOVERABILITY_MAP.get(cat, "requires_review")

    # Override for exhausted retries
    if retry_count >= max_retries and recoverability == "recoverable":
        recoverability = "recoverable"  # Still recoverable but blocked by policy

    # Override for description flags
    if description:
        desc_lower = description.lower()
        if "cancelled_subscription" in desc_lower:
            recoverability = "non_recoverable"
        elif "disputed_invoice" in desc_lower:
            recoverability = "requires_review"
        elif "opted_out_customer" in desc_lower:
            recoverability = "recoverable"  # Technically recoverable but comms blocked

    risk_score = Decimal(str(round(min(100.0, max(0.0, float(base))), 2)))

    # Priority from score
    if risk_score >= 80:
        priority = "critical"
    elif risk_score >= 60:
        priority = "high"
    elif risk_score >= 40:
        priority = "medium"
    else:
        priority = "low"

    requires_human_review = (
        recoverability == "requires_review"
        or cat == "unknown"
        or (description and "disputed" in description.lower())
    )

    return {
        "risk_score": risk_score,
        "recoverability": recoverability,
        "priority": priority,
        "requires_human_review": bool(requires_human_review),
        "risk_factors": risk_factors,
    }
