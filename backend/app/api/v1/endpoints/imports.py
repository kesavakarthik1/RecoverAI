"""CSV import and batch processing endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ValidationError
from app.models.batch_import import BatchImport
from app.models.merchant import Merchant
from app.models.transaction import Transaction
from app.services.csv_import import validate_and_parse_csv
from app.services.synthetic_data import generate_synthetic_dataset

router = APIRouter()

DEFAULT_MERCHANT_ID = "merchant-demo-001"


async def _ensure_demo_merchant(db: AsyncSession) -> Merchant:
    """Create the demo merchant if it doesn't exist."""
    result = await db.execute(
        select(Merchant).where(Merchant.id == DEFAULT_MERCHANT_ID)
    )
    merchant = result.scalar_one_or_none()
    if not merchant:
        merchant = Merchant(
            id=DEFAULT_MERCHANT_ID,
            name="Demo Merchant",
            email="demo@recoverai.local",
            business_type="ecommerce",
            currency="INR",
        )
        db.add(merchant)
        await db.flush()
    return merchant


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile = File(...),
    merchant_id: str = Form(default=DEFAULT_MERCHANT_ID),
    db: AsyncSession = Depends(get_db),
):
    """Upload and validate a CSV file of transactions."""
    await _ensure_demo_merchant(db)

    # File size check
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValidationError(
            f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # File type check
    if not (file.filename or "").lower().endswith(".csv"):
        raise ValidationError("Only CSV files are accepted.")

    batch_id = str(uuid.uuid4())

    # Create batch record
    batch = BatchImport(
        id=batch_id,
        filename=file.filename or "upload.csv",
        merchant_id=merchant_id,
        status="validating",
        started_at=datetime.now(timezone.utc),
    )
    db.add(batch)
    await db.flush()

    # Validate CSV
    parse_result = validate_and_parse_csv(
        content,
        merchant_id=merchant_id,
        max_rows=10000,
    )

    batch.total_rows = parse_result["total_rows"]
    batch.valid_rows = parse_result["valid_count"]
    batch.invalid_rows = parse_result["invalid_count"]
    batch.duplicate_rows = parse_result["duplicate_count"]
    batch.validation_errors = parse_result["invalid_rows"][:50]  # Cap error list
    batch.status = "processing"
    db.add(batch)
    await db.flush()

    # Import valid rows
    imported = 0
    for row in parse_result["valid_rows"]:
        # Check idempotency — skip if external_id already exists for this merchant
        existing = await db.execute(
            select(Transaction).where(
                Transaction.external_id == row["external_id"],
                Transaction.merchant_id == merchant_id,
            )
        )
        if existing.scalar_one_or_none():
            batch.duplicate_rows = (batch.duplicate_rows or 0) + 1
            continue

        txn = Transaction(
            id=str(uuid.uuid4()),
            external_id=row["external_id"],
            batch_id=batch_id,
            merchant_id=merchant_id,
            customer_ref=row["customer_ref"],
            amount=row["amount"],
            currency=row["currency"],
            transaction_type=row["transaction_type"],
            status=row["status"],
            failure_reason=row.get("failure_reason") or None,
            failure_category=row.get("failure_category") or None,
            failure_code=row.get("failure_code") or None,
            retry_count=row.get("retry_count", 0),
            payment_method=row.get("payment_method") or None,
            gateway=row.get("gateway") or None,
            description=row.get("description") or None,
            is_synthetic=row.get("is_synthetic", False),
            recoverability="unknown",
            recovery_status="pending",
        )
        db.add(txn)
        imported += 1

    batch.imported_rows = imported
    batch.status = "completed" if parse_result["invalid_count"] == 0 else "partial"
    batch.completed_at = datetime.now(timezone.utc)
    db.add(batch)
    await db.flush()

    return {
        "batch_id": batch_id,
        "filename": file.filename,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "invalid_rows": batch.invalid_rows,
        "duplicate_rows": batch.duplicate_rows,
        "imported_rows": imported,
        "validation_errors": parse_result["invalid_rows"][:10],
    }


@router.post("/generate-synthetic", status_code=status.HTTP_201_CREATED)
async def generate_synthetic(
    count: int = 100,
    seed: int = 42,
    merchant_id: str = DEFAULT_MERCHANT_ID,
    db: AsyncSession = Depends(get_db),
):
    """Generate a synthetic dataset and import it into the database."""
    await _ensure_demo_merchant(db)

    if count < 10 or count > 500:
        raise ValidationError("Count must be between 10 and 500.")

    batch_id = str(uuid.uuid4())
    dataset = generate_synthetic_dataset(count=count, seed=seed, merchant_id=merchant_id)

    batch = BatchImport(
        id=batch_id,
        filename=f"synthetic_seed{seed}_n{count}.csv",
        merchant_id=merchant_id,
        status="processing",
        is_synthetic=True,
        started_at=datetime.now(timezone.utc),
        total_rows=len(dataset["records"]),
    )
    db.add(batch)
    await db.flush()

    imported = 0
    for row in dataset["records"]:
        from datetime import datetime as dt
        txn = Transaction(
            id=row.get("id") or str(uuid.uuid4()),
            external_id=row.get("external_id"),
            batch_id=batch_id,
            merchant_id=merchant_id,
            customer_ref=row["customer_ref"],
            amount=row["amount"],
            currency=row.get("currency", "INR"),
            transaction_type=row["transaction_type"],
            status=row["status"],
            failure_reason=row.get("failure_reason") or None,
            failure_category=row.get("failure_category") or None,
            failure_timestamp=(
                dt.fromisoformat(row["failure_timestamp"])
                if row.get("failure_timestamp") else None
            ),
            retry_count=row.get("retry_count", 0),
            risk_score=row.get("risk_score"),
            recoverability=row.get("recoverability", "unknown"),
            recovery_status=row.get("recovery_status", "pending"),
            payment_method=row.get("payment_method"),
            gateway=row.get("gateway"),
            description=row.get("description"),
            is_synthetic=True,
            synthetic_ground_truth_recoverable=row.get("synthetic_ground_truth_recoverable"),
            synthetic_recovery_outcome=row.get("synthetic_recovery_outcome"),
        )
        db.add(txn)
        imported += 1

    batch.imported_rows = imported
    batch.valid_rows = imported
    batch.invalid_rows = len(dataset["invalid_records"])
    batch.duplicate_rows = len(dataset["duplicate_records"])
    batch.status = "completed"
    batch.completed_at = datetime.now(timezone.utc)
    db.add(batch)
    await db.flush()

    return {
        "batch_id": batch_id,
        "status": "completed",
        "imported_rows": imported,
        "invalid_rows": len(dataset["invalid_records"]),
        "duplicate_rows": len(dataset["duplicate_records"]),
        "metadata": dataset["metadata"],
    }


@router.get("")
async def list_batches(
    merchant_id: str = DEFAULT_MERCHANT_ID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BatchImport)
        .where(BatchImport.merchant_id == merchant_id)
        .order_by(BatchImport.created_at.desc())
        .limit(50)
    )
    batches = result.scalars().all()
    return [
        {
            "id": b.id,
            "filename": b.filename,
            "status": b.status,
            "total_rows": b.total_rows,
            "valid_rows": b.valid_rows,
            "invalid_rows": b.invalid_rows,
            "imported_rows": b.imported_rows,
            "is_synthetic": b.is_synthetic,
            "created_at": b.created_at.isoformat(),
            "completed_at": b.completed_at.isoformat() if b.completed_at else None,
        }
        for b in batches
    ]


@router.get("/template")
async def get_csv_template():
    """Return CSV column documentation."""
    return {
        "required_columns": [
            "external_id", "customer_ref", "amount", "currency",
            "transaction_type", "status",
        ],
        "optional_columns": [
            "failure_reason", "failure_category", "failure_code",
            "retry_count", "payment_method", "gateway", "description",
            "is_synthetic",
        ],
        "valid_values": {
            "transaction_type": ["payment", "subscription", "invoice", "checkout"],
            "status": ["pending", "success", "failed", "abandoned", "overdue", "cancelled"],
            "failure_category": [
                "temp_failure", "insufficient_funds", "auth_required",
                "invalid_details", "fraud", "unknown",
            ],
            "currency": ["INR", "USD", "EUR", "GBP", "AED", "SGD"],
        },
        "example_row": {
            "external_id": "TXN-001",
            "customer_ref": "CUST-0001",
            "amount": "5000.00",
            "currency": "INR",
            "transaction_type": "payment",
            "status": "failed",
            "failure_reason": "Gateway timeout",
            "failure_category": "temp_failure",
            "retry_count": "0",
        },
    }
