"""
Synthetic Dataset Generator for RecoverAI.

Produces a reproducible, labeled dataset covering all required scenarios:
- Retryable temporary failures
- Non-retryable failures
- Abandoned checkouts
- Failed subscriptions
- Overdue invoices
- Paid transactions
- Opted-out customers
- Cancelled subscriptions
- Disputed invoices
- Exhausted retry budgets
- Human-approval required cases
- Duplicate rows
- Invalid rows
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

MERCHANT_ID = "merchant-demo-001"

# ── Failure categories ────────────────────────────────────────────────────────
FAILURE_CATEGORIES = {
    "temp_failure": {
        "reasons": [
            "Gateway timeout",
            "Network error",
            "Processor unavailable",
            "Temporary service disruption",
        ],
        "retryable": True,
        "ground_truth_recoverable": True,
    },
    "insufficient_funds": {
        "reasons": [
            "Insufficient balance",
            "Card limit exceeded",
            "Daily limit reached",
        ],
        "retryable": False,
        "ground_truth_recoverable": False,
    },
    "auth_required": {
        "reasons": [
            "3DS authentication required",
            "OTP verification failed",
            "Strong customer authentication needed",
        ],
        "retryable": False,
        "ground_truth_recoverable": True,  # Customer can re-authenticate
    },
    "invalid_details": {
        "reasons": [
            "Card number invalid",
            "Expired card",
            "Invalid CVV",
            "Billing address mismatch",
        ],
        "retryable": False,
        "ground_truth_recoverable": False,
    },
    "fraud": {
        "reasons": [
            "Suspected fraud",
            "Security restriction",
            "Card blocked by issuer",
            "Velocity check failed",
        ],
        "retryable": False,
        "ground_truth_recoverable": False,
    },
    "unknown": {
        "reasons": ["Unknown error", "Undefined failure"],
        "retryable": False,
        "ground_truth_recoverable": None,  # Requires human review
    },
}

PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet", "emi"]
GATEWAYS = ["razorpay", "stripe", "payu", "ccavenue"]


def _uid() -> str:
    return str(uuid.uuid4())


def _ts(days_ago: int = 0, hours_ago: int = 0) -> str:
    """ISO timestamp N days/hours in the past."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)
    return dt.isoformat()


def _amount(low: int = 500, high: int = 100000) -> str:
    return str(round(random.uniform(low, high), 2))


def generate_synthetic_dataset(
    count: int = 100,
    seed: int = 42,
    merchant_id: str = MERCHANT_ID,
) -> Dict[str, Any]:
    """
    Generate a synthetic transaction dataset.

    Returns a dict with:
      - records: List of transaction dicts (valid rows)
      - duplicate_records: rows that duplicate a valid record
      - invalid_records: rows with intentional validation errors
      - metadata: generation parameters and label counts
    """
    random.seed(seed)

    records: List[Dict[str, Any]] = []
    customer_ids = [f"CUST-{i:04d}" for i in range(1, 31)]

    # ── Scenario distribution (must add up to ~count) ─────────────────────────
    distribution = {
        "paid": int(count * 0.20),              # 20% successful
        "temp_failure": int(count * 0.15),       # 15% retryable temp failures
        "temp_failure_retry_exhausted": int(count * 0.05),  # 5% exhausted
        "insufficient_funds": int(count * 0.08),  # 8% NSF
        "auth_required": int(count * 0.07),       # 7% needs re-auth
        "invalid_details": int(count * 0.05),     # 5% invalid card
        "fraud": int(count * 0.05),               # 5% fraud-blocked
        "unknown_review": int(count * 0.05),      # 5% unknown → human review
        "abandoned_checkout": int(count * 0.10),  # 10% abandoned
        "failed_subscription": int(count * 0.08), # 8% sub failure
        "cancelled_subscription": int(count * 0.03),  # 3% cancelled sub
        "overdue_invoice": int(count * 0.05),     # 5% overdue
        "disputed_invoice": int(count * 0.02),    # 2% disputed
        "opted_out_customer": int(count * 0.02),  # 2% opted-out comms
    }

    # Fill remainder with temp_failure
    assigned = sum(distribution.values())
    distribution["temp_failure"] += max(0, count - assigned)

    def _base_record(txn_type: str, status: str, customer_ref: str) -> Dict[str, Any]:
        return {
            "id": _uid(),
            "external_id": f"EXT-{_uid()[:8].upper()}",
            "merchant_id": merchant_id,
            "customer_ref": customer_ref,
            "amount": _amount(),
            "currency": "INR",
            "transaction_type": txn_type,
            "status": status,
            "payment_method": random.choice(PAYMENT_METHODS),
            "gateway": random.choice(GATEWAYS),
            "failure_reason": None,
            "failure_category": None,
            "failure_timestamp": None,
            "failure_code": None,
            "retry_count": 0,
            "risk_score": None,
            "recoverability": "unknown",
            "recovery_status": "pending",
            # Ground-truth labels for evaluation
            "synthetic_ground_truth_recoverable": None,
            "synthetic_recovery_outcome": None,
            "is_synthetic": True,
            "description": None,
        }

    # ── 1. Paid / successful ─────────────────────────────────────────────────
    for _ in range(distribution["paid"]):
        cust = random.choice(customer_ids)
        r = _base_record("payment", "success", cust)
        r.update({
            "recoverability": "not_applicable",
            "recovery_status": "closed",
            "synthetic_ground_truth_recoverable": False,
            "synthetic_recovery_outcome": "not_applicable",
        })
        records.append(r)

    # ── 2. Temp failure (retryable) ──────────────────────────────────────────
    for _ in range(distribution["temp_failure"]):
        cust = random.choice(customer_ids)
        cat = "temp_failure"
        info = FAILURE_CATEGORIES[cat]
        r = _base_record("payment", "failed", cust)
        r.update({
            "failure_reason": random.choice(info["reasons"]),
            "failure_category": cat,
            "failure_timestamp": _ts(days_ago=random.randint(0, 3)),
            "retry_count": random.randint(0, 2),
            "risk_score": str(round(random.uniform(30, 60), 2)),
            "recoverability": "recoverable",
            "recovery_status": "pending",
            "synthetic_ground_truth_recoverable": True,
            "synthetic_recovery_outcome": random.choice(["recovered", "failed"]),
        })
        records.append(r)

    # ── 3. Temp failure with exhausted retry budget ──────────────────────────
    for _ in range(distribution["temp_failure_retry_exhausted"]):
        cust = random.choice(customer_ids)
        r = _base_record("payment", "failed", cust)
        r.update({
            "failure_reason": "Gateway timeout",
            "failure_category": "temp_failure",
            "failure_timestamp": _ts(days_ago=random.randint(4, 10)),
            "retry_count": 3,  # At limit
            "risk_score": str(round(random.uniform(60, 80), 2)),
            "recoverability": "recoverable",
            "recovery_status": "blocked",
            "synthetic_ground_truth_recoverable": True,
            "synthetic_recovery_outcome": "blocked_retry_limit",
        })
        records.append(r)

    # ── 4. Insufficient funds ────────────────────────────────────────────────
    for _ in range(distribution["insufficient_funds"]):
        cust = random.choice(customer_ids)
        cat = "insufficient_funds"
        info = FAILURE_CATEGORIES[cat]
        r = _base_record("payment", "failed", cust)
        r.update({
            "failure_reason": random.choice(info["reasons"]),
            "failure_category": cat,
            "failure_timestamp": _ts(days_ago=random.randint(0, 7)),
            "retry_count": 1,
            "risk_score": str(round(random.uniform(50, 75), 2)),
            "recoverability": "non_recoverable",
            "recovery_status": "pending",
            "synthetic_ground_truth_recoverable": False,
            "synthetic_recovery_outcome": "not_recoverable",
        })
        records.append(r)

    # ── 5. Auth required ─────────────────────────────────────────────────────
    for _ in range(distribution["auth_required"]):
        cust = random.choice(customer_ids)
        cat = "auth_required"
        info = FAILURE_CATEGORIES[cat]
        r = _base_record("payment", "failed", cust)
        r.update({
            "failure_reason": random.choice(info["reasons"]),
            "failure_category": cat,
            "failure_timestamp": _ts(hours_ago=random.randint(1, 48)),
            "retry_count": 0,
            "risk_score": str(round(random.uniform(20, 45), 2)),
            "recoverability": "recoverable",
            "recovery_status": "pending",
            "synthetic_ground_truth_recoverable": True,
            "synthetic_recovery_outcome": random.choice(["recovered", "failed"]),
        })
        records.append(r)

    # ── 6. Invalid details ───────────────────────────────────────────────────
    for _ in range(distribution["invalid_details"]):
        cust = random.choice(customer_ids)
        cat = "invalid_details"
        info = FAILURE_CATEGORIES[cat]
        r = _base_record("payment", "failed", cust)
        r.update({
            "failure_reason": random.choice(info["reasons"]),
            "failure_category": cat,
            "failure_timestamp": _ts(days_ago=random.randint(0, 5)),
            "retry_count": 1,
            "risk_score": str(round(random.uniform(70, 90), 2)),
            "recoverability": "non_recoverable",
            "recovery_status": "pending",
            "synthetic_ground_truth_recoverable": False,
            "synthetic_recovery_outcome": "not_recoverable",
        })
        records.append(r)

    # ── 7. Fraud / security ──────────────────────────────────────────────────
    for _ in range(distribution["fraud"]):
        cust = random.choice(customer_ids)
        cat = "fraud"
        info = FAILURE_CATEGORIES[cat]
        r = _base_record("payment", "failed", cust)
        r.update({
            "failure_reason": random.choice(info["reasons"]),
            "failure_category": cat,
            "failure_timestamp": _ts(days_ago=random.randint(0, 14)),
            "retry_count": 0,
            "risk_score": str(round(random.uniform(85, 100), 2)),
            "recoverability": "non_recoverable",
            "recovery_status": "blocked",
            "synthetic_ground_truth_recoverable": False,
            "synthetic_recovery_outcome": "blocked_fraud",
        })
        records.append(r)

    # ── 8. Unknown — requires human review ───────────────────────────────────
    for _ in range(distribution["unknown_review"]):
        cust = random.choice(customer_ids)
        r = _base_record("payment", "failed", cust)
        r.update({
            "failure_reason": "Unknown error",
            "failure_category": "unknown",
            "failure_timestamp": _ts(days_ago=random.randint(0, 5)),
            "retry_count": 0,
            "risk_score": str(round(random.uniform(40, 65), 2)),
            "recoverability": "requires_review",
            "recovery_status": "pending",
            "synthetic_ground_truth_recoverable": None,
            "synthetic_recovery_outcome": "human_review",
        })
        records.append(r)

    # ── 9. Abandoned checkout ─────────────────────────────────────────────────
    for _ in range(distribution["abandoned_checkout"]):
        cust = random.choice(customer_ids)
        r = _base_record("checkout", "abandoned", cust)
        hours = random.randint(1, 72)
        r.update({
            "failure_reason": "Session abandoned",
            "failure_category": "temp_failure",
            "failure_timestamp": _ts(hours_ago=hours),
            "retry_count": 0,
            "risk_score": str(round(random.uniform(25, 55), 2)),
            "recoverability": "recoverable",
            "recovery_status": "pending",
            "description": f"Cart abandoned {hours}h ago",
            "synthetic_ground_truth_recoverable": True,
            "synthetic_recovery_outcome": random.choice(["recovered", "failed", "no_response"]),
        })
        records.append(r)

    # ── 10. Failed subscription ───────────────────────────────────────────────
    for _ in range(distribution["failed_subscription"]):
        cust = random.choice(customer_ids)
        r = _base_record("subscription", "failed", cust)
        cat = random.choice(["temp_failure", "insufficient_funds", "auth_required"])
        info = FAILURE_CATEGORIES[cat]
        r.update({
            "failure_reason": random.choice(info["reasons"]),
            "failure_category": cat,
            "failure_timestamp": _ts(days_ago=random.randint(0, 7)),
            "retry_count": random.randint(0, 2),
            "risk_score": str(round(random.uniform(35, 65), 2)),
            "recoverability": "recoverable" if info["ground_truth_recoverable"] else "non_recoverable",
            "recovery_status": "pending",
            "synthetic_ground_truth_recoverable": info["ground_truth_recoverable"],
            "synthetic_recovery_outcome": (
                random.choice(["recovered", "failed"]) if info["ground_truth_recoverable"]
                else "not_recoverable"
            ),
        })
        records.append(r)

    # ── 11. Cancelled subscription (must not be retried) ─────────────────────
    for _ in range(distribution["cancelled_subscription"]):
        cust = random.choice(customer_ids)
        r = _base_record("subscription", "failed", cust)
        r.update({
            "failure_reason": "Subscription cancelled",
            "failure_category": "invalid_details",
            "failure_timestamp": _ts(days_ago=random.randint(1, 30)),
            "retry_count": 0,
            "risk_score": str(round(random.uniform(10, 30), 2)),
            "recoverability": "non_recoverable",
            "recovery_status": "closed",
            "description": "cancelled_subscription",  # Flag for policy engine
            "synthetic_ground_truth_recoverable": False,
            "synthetic_recovery_outcome": "stopped_cancelled",
        })
        records.append(r)

    # ── 12. Overdue invoice ───────────────────────────────────────────────────
    for _ in range(distribution["overdue_invoice"]):
        cust = random.choice(customer_ids)
        r = _base_record("invoice", "overdue", cust)
        days = random.randint(5, 90)
        r.update({
            "failure_reason": f"Invoice overdue by {days} days",
            "failure_category": "temp_failure",
            "failure_timestamp": _ts(days_ago=days),
            "retry_count": random.randint(0, 2),
            "risk_score": str(round(min(90, days * 0.8 + random.uniform(0, 10)), 2)),
            "recoverability": "recoverable",
            "recovery_status": "pending",
            "description": f"overdue_{days}_days",
            "synthetic_ground_truth_recoverable": True,
            "synthetic_recovery_outcome": random.choice(["recovered", "failed", "partial"]),
        })
        records.append(r)

    # ── 13. Disputed invoice ─────────────────────────────────────────────────
    for _ in range(distribution["disputed_invoice"]):
        cust = random.choice(customer_ids)
        r = _base_record("invoice", "overdue", cust)
        r.update({
            "failure_reason": "Invoice disputed by customer",
            "failure_category": "unknown",
            "failure_timestamp": _ts(days_ago=random.randint(10, 60)),
            "retry_count": 0,
            "risk_score": str(round(random.uniform(60, 85), 2)),
            "recoverability": "requires_review",
            "recovery_status": "human_review",
            "description": "disputed_invoice",
            "synthetic_ground_truth_recoverable": None,
            "synthetic_recovery_outcome": "human_review",
        })
        records.append(r)

    # ── 14. Opted-out customer ────────────────────────────────────────────────
    for _ in range(distribution["opted_out_customer"]):
        cust = random.choice(customer_ids)
        r = _base_record("payment", "failed", cust)
        r.update({
            "failure_reason": "Gateway timeout",
            "failure_category": "temp_failure",
            "failure_timestamp": _ts(days_ago=random.randint(0, 5)),
            "retry_count": 0,
            "risk_score": str(round(random.uniform(30, 50), 2)),
            "recoverability": "recoverable",
            "recovery_status": "blocked",
            "description": "opted_out_customer",  # Policy engine checks this
            "synthetic_ground_truth_recoverable": True,
            "synthetic_recovery_outcome": "blocked_opted_out",
        })
        records.append(r)

    # ── Duplicate rows (same external_id as first record) ────────────────────
    dup_count = max(2, int(count * 0.03))
    duplicate_records: List[Dict[str, Any]] = []
    for i in range(dup_count):
        source = records[i % len(records)].copy()
        duplicate_records.append(source)

    # ── Invalid rows ─────────────────────────────────────────────────────────
    invalid_records: List[Dict[str, Any]] = [
        {"id": _uid(), "external_id": "", "merchant_id": "", "customer_ref": "CUST-0001",
         "amount": "not-a-number", "currency": "INR", "transaction_type": "payment",
         "status": "failed", "_error": "invalid_amount"},
        {"id": _uid(), "external_id": f"EXT-{_uid()[:8]}", "merchant_id": merchant_id,
         "customer_ref": "", "amount": "1500.00", "currency": "XYZ",
         "transaction_type": "payment", "status": "invalid_status",
         "_error": "invalid_currency_status"},
        {"id": _uid(), "merchant_id": merchant_id, "amount": "-500",
         "_error": "missing_required_fields_negative_amount"},
    ]

    # ── Metadata ─────────────────────────────────────────────────────────────
    label_counts: Dict[str, int] = {}
    for r in records:
        outcome = r.get("synthetic_recovery_outcome") or "n/a"
        label_counts[outcome] = label_counts.get(outcome, 0) + 1

    return {
        "records": records,
        "duplicate_records": duplicate_records,
        "invalid_records": invalid_records,
        "metadata": {
            "seed": seed,
            "count": len(records),
            "duplicate_count": len(duplicate_records),
            "invalid_count": len(invalid_records),
            "merchant_id": merchant_id,
            "label_distribution": label_counts,
            "distribution": distribution,
        },
    }
