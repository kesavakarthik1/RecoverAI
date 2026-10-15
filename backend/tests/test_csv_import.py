"""
Tests for CSV validation and import service.
Covers: column validation, missing values, duplicates, type validation, formula injection.
"""
import pytest
from decimal import Decimal

from app.services.csv_import import validate_and_parse_csv, _sanitize_csv_value


class TestCsvValidation:
    def _make_csv(self, rows: list[dict]) -> bytes:
        if not rows:
            return b"external_id,customer_ref,amount,currency,transaction_type,status\n"
        headers = list(rows[0].keys())
        lines = [",".join(headers)]
        for row in rows:
            lines.append(",".join(str(row.get(h, "")) for h in headers))
        return "\n".join(lines).encode("utf-8")

    def test_valid_single_row(self):
        csv_bytes = self._make_csv([{
            "external_id": "TXN-001", "customer_ref": "CUST-001",
            "amount": "5000.00", "currency": "INR",
            "transaction_type": "payment", "status": "failed",
        }])
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["valid_count"] == 1
        assert result["invalid_count"] == 0
        assert result["valid_rows"][0]["amount"] == Decimal("5000.00")

    def test_missing_required_column(self):
        csv_bytes = b"external_id,customer_ref,amount\nTXN-001,CUST-001,500\n"
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["invalid_count"] == 1
        assert result["valid_count"] == 0
        assert any("Missing required columns" in e["errors"][0]
                   for e in result["invalid_rows"])

    def test_invalid_amount(self):
        csv_bytes = self._make_csv([{
            "external_id": "TXN-001", "customer_ref": "CUST-001",
            "amount": "not-a-number", "currency": "INR",
            "transaction_type": "payment", "status": "failed",
        }])
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["invalid_count"] == 1
        assert any("Invalid amount" in e for r in result["invalid_rows"] for e in r["errors"])

    def test_negative_amount_rejected(self):
        csv_bytes = self._make_csv([{
            "external_id": "TXN-001", "customer_ref": "CUST-001",
            "amount": "-500.00", "currency": "INR",
            "transaction_type": "payment", "status": "failed",
        }])
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["invalid_count"] == 1

    def test_invalid_transaction_type(self):
        csv_bytes = self._make_csv([{
            "external_id": "TXN-001", "customer_ref": "CUST-001",
            "amount": "5000", "currency": "INR",
            "transaction_type": "invalid_type", "status": "failed",
        }])
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["invalid_count"] == 1

    def test_invalid_status(self):
        csv_bytes = self._make_csv([{
            "external_id": "TXN-001", "customer_ref": "CUST-001",
            "amount": "5000", "currency": "INR",
            "transaction_type": "payment", "status": "bad_status",
        }])
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["invalid_count"] == 1

    def test_unsupported_currency(self):
        csv_bytes = self._make_csv([{
            "external_id": "TXN-001", "customer_ref": "CUST-001",
            "amount": "5000", "currency": "ZZZ",
            "transaction_type": "payment", "status": "failed",
        }])
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["invalid_count"] == 1

    def test_duplicate_external_id_detected(self):
        csv_bytes = self._make_csv([
            {"external_id": "DUP-001", "customer_ref": "CUST-001",
             "amount": "5000", "currency": "INR",
             "transaction_type": "payment", "status": "failed"},
            {"external_id": "DUP-001", "customer_ref": "CUST-002",
             "amount": "3000", "currency": "INR",
             "transaction_type": "payment", "status": "failed"},
        ])
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["duplicate_count"] == 1
        assert result["valid_count"] == 1

    def test_empty_file(self):
        result = validate_and_parse_csv(b"", merchant_id="merchant-001")
        assert result["invalid_count"] >= 1

    def test_multiple_valid_rows(self):
        rows = [
            {"external_id": f"TXN-{i:03d}", "customer_ref": f"CUST-{i:03d}",
             "amount": "1000", "currency": "INR",
             "transaction_type": "payment", "status": "failed"}
            for i in range(10)
        ]
        csv_bytes = self._make_csv(rows)
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["valid_count"] == 10
        assert result["invalid_count"] == 0

    def test_valid_failure_category_accepted(self):
        csv_bytes = self._make_csv([{
            "external_id": "TXN-001", "customer_ref": "CUST-001",
            "amount": "5000", "currency": "INR",
            "transaction_type": "payment", "status": "failed",
            "failure_category": "temp_failure",
        }])
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["valid_count"] == 1
        assert result["valid_rows"][0]["failure_category"] == "temp_failure"

    def test_invalid_failure_category_rejected(self):
        csv_bytes = self._make_csv([{
            "external_id": "TXN-001", "customer_ref": "CUST-001",
            "amount": "5000", "currency": "INR",
            "transaction_type": "payment", "status": "failed",
            "failure_category": "definitely_not_valid",
        }])
        result = validate_and_parse_csv(csv_bytes, merchant_id="merchant-001")
        assert result["invalid_count"] == 1


class TestCsvFormulaInjection:
    def test_formula_prefix_stripped(self):
        assert _sanitize_csv_value("=SUM(1+1)") == "'=SUM(1+1)"
        assert _sanitize_csv_value("+CMD") == "'+CMD"
        assert _sanitize_csv_value("-1+1") == "'-1+1"
        assert _sanitize_csv_value("@SUM") == "'@SUM"

    def test_safe_values_unchanged(self):
        assert _sanitize_csv_value("normal text") == "normal text"
        assert _sanitize_csv_value("5000.00") == "5000.00"
        assert _sanitize_csv_value("CUST-001") == "CUST-001"
