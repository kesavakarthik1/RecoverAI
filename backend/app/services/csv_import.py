"""
CSV Import Service.
Validates and imports transaction CSV files.
Handles duplicates, invalid rows, and schema validation.
"""
from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = {
    "external_id", "customer_ref", "amount", "currency",
    "transaction_type", "status",
}

VALID_TRANSACTION_TYPES = {"payment", "subscription", "invoice", "checkout"}
VALID_STATUSES = {"pending", "success", "failed", "abandoned", "overdue", "cancelled"}
VALID_CURRENCIES = {"INR", "USD", "EUR", "GBP", "AED", "SGD"}
VALID_FAILURE_CATEGORIES = {
    "temp_failure", "insufficient_funds", "auth_required",
    "invalid_details", "fraud", "unknown", None, "",
}


def _sanitize_csv_value(value: str) -> str:
    """
    Prevent CSV formula injection.
    Strip leading =, +, -, @ characters that Excel/Sheets treat as formulas.
    """
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def validate_and_parse_csv(
    content: bytes,
    *,
    max_rows: int = 10000,
    merchant_id: str = "unknown",
) -> Dict[str, Any]:
    """
    Parse and validate a CSV file.

    Returns:
        {
          "valid_rows": [...],
          "invalid_rows": [{row_number, row_data, errors}],
          "duplicate_external_ids": [...],
          "total_rows": int,
          "valid_count": int,
          "invalid_count": int,
          "duplicate_count": int,
        }
    """
    try:
        text = content.decode("utf-8-sig")  # Handle BOM
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return {
            "valid_rows": [],
            "invalid_rows": [{"row_number": 0, "errors": ["File is empty or has no header row"]}],
            "duplicate_external_ids": [],
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 1,
            "duplicate_count": 0,
        }

    # Normalise column names (strip whitespace, lowercase)
    raw_fields = [f.strip().lower() for f in reader.fieldnames]
    missing_required = REQUIRED_COLUMNS - set(raw_fields)
    if missing_required:
        return {
            "valid_rows": [],
            "invalid_rows": [{
                "row_number": 0,
                "errors": [f"Missing required columns: {', '.join(sorted(missing_required))}"],
            }],
            "duplicate_external_ids": [],
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 1,
            "duplicate_count": 0,
        }

    valid_rows: List[Dict[str, Any]] = []
    invalid_rows: List[Dict[str, Any]] = []
    seen_external_ids: set = set()
    duplicate_external_ids: List[str] = []

    for row_num, raw_row in enumerate(reader, start=2):
        if row_num > max_rows + 1:
            break

        # Normalise keys
        row = {k.strip().lower(): (v or "").strip() for k, v in raw_row.items()}
        errors: List[str] = []

        # ── Required field presence ──────────────────────────────────────────
        for col in REQUIRED_COLUMNS:
            if not row.get(col):
                errors.append(f"Required field '{col}' is missing or empty")

        if errors:
            invalid_rows.append({"row_number": row_num, "row_data": row, "errors": errors})
            continue

        # ── Duplicate check ──────────────────────────────────────────────────
        ext_id = row.get("external_id", "")
        if ext_id in seen_external_ids:
            duplicate_external_ids.append(ext_id)
            invalid_rows.append({
                "row_number": row_num,
                "row_data": row,
                "errors": [f"Duplicate external_id: {ext_id}"],
            })
            continue
        seen_external_ids.add(ext_id)

        # ── Amount validation ────────────────────────────────────────────────
        try:
            amount = Decimal(row["amount"])
            if amount <= 0:
                errors.append(f"Amount must be positive, got: {row['amount']}")
        except InvalidOperation:
            errors.append(f"Invalid amount value: {row['amount']}")
            amount = None

        # ── Currency ─────────────────────────────────────────────────────────
        currency = row.get("currency", "INR").upper()
        if currency not in VALID_CURRENCIES:
            errors.append(f"Unsupported currency: {currency}")

        # ── Transaction type ─────────────────────────────────────────────────
        txn_type = row.get("transaction_type", "").lower()
        if txn_type not in VALID_TRANSACTION_TYPES:
            errors.append(f"Invalid transaction_type: {txn_type}. Must be one of {VALID_TRANSACTION_TYPES}")

        # ── Status ────────────────────────────────────────────────────────────
        status = row.get("status", "").lower()
        if status not in VALID_STATUSES:
            errors.append(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")

        # ── Failure category (optional) ────────────────────────────────────
        failure_cat = row.get("failure_category", "").lower() or None
        if failure_cat and failure_cat not in VALID_FAILURE_CATEGORIES:
            errors.append(f"Invalid failure_category: {failure_cat}")

        if errors:
            invalid_rows.append({"row_number": row_num, "row_data": row, "errors": errors})
            continue

        # ── Build clean record ─────────────────────────────────────────────
        parsed: Dict[str, Any] = {
            "external_id": _sanitize_csv_value(ext_id),
            "merchant_id": merchant_id,
            "customer_ref": _sanitize_csv_value(row.get("customer_ref", "")),
            "amount": amount,
            "currency": currency,
            "transaction_type": txn_type,
            "status": status,
            "failure_reason": _sanitize_csv_value(row.get("failure_reason", "")),
            "failure_category": failure_cat,
            "failure_code": row.get("failure_code", "") or None,
            "retry_count": _safe_int(row.get("retry_count", "0")),
            "payment_method": row.get("payment_method", "") or None,
            "gateway": row.get("gateway", "") or None,
            "description": _sanitize_csv_value(row.get("description", "")),
            "is_synthetic": row.get("is_synthetic", "false").lower() == "true",
        }
        valid_rows.append(parsed)

    return {
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "duplicate_external_ids": duplicate_external_ids,
        "total_rows": row_num - 1 if 'row_num' in dir() else 0,
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
        "duplicate_count": len(duplicate_external_ids),
    }


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
