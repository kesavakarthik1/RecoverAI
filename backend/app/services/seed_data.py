"""
Auto-seed service.

On first startup (empty database), automatically:
1. Creates the demo merchant
2. Generates 100 synthetic transactions (seed=42)
3. Runs the recovery agent on all eligible transactions
4. Runs the 3-strategy evaluation
5. Records everything in the audit trail

This ensures the dashboard is immediately populated when the project is first run.
The seed only runs when the database has zero transactions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.merchant import Merchant
from app.models.transaction import Transaction
from app.services.synthetic_data import generate_synthetic_dataset

logger = get_logger(__name__)

DEMO_MERCHANT_ID = "merchant-demo-001"
SEED = 42
COUNT = 100


async def _ensure_merchant(db: AsyncSession) -> Merchant:
    result = await db.execute(select(Merchant).where(Merchant.id == DEMO_MERCHANT_ID))
    merchant = result.scalar_one_or_none()
    if not merchant:
        merchant = Merchant(
            id=DEMO_MERCHANT_ID,
            name="Demo Merchant",
            email="demo@recoverai.local",
            business_type="ecommerce",
            currency="INR",
        )
        db.add(merchant)
        await db.flush()
    return merchant


async def _import_transactions(db: AsyncSession, batch_id: str) -> int:
    """Import synthetic transactions into the database."""
    from app.models.batch_import import BatchImport

    dataset = generate_synthetic_dataset(count=COUNT, seed=SEED, merchant_id=DEMO_MERCHANT_ID)

    batch = BatchImport(
        id=batch_id,
        filename=f"auto_seed_n{COUNT}_seed{SEED}.csv",
        merchant_id=DEMO_MERCHANT_ID,
        status="processing",
        is_synthetic=True,
        started_at=datetime.now(timezone.utc),
        total_rows=len(dataset["records"]),
    )
    db.add(batch)
    await db.flush()

    imported = 0
    for row in dataset["records"]:
        txn = Transaction(
            id=row.get("id") or str(uuid.uuid4()),
            external_id=row.get("external_id"),
            batch_id=batch_id,
            merchant_id=DEMO_MERCHANT_ID,
            customer_ref=row["customer_ref"],
            amount=Decimal(str(row["amount"])),
            currency=row.get("currency", "INR"),
            transaction_type=row["transaction_type"],
            status=row["status"],
            failure_reason=row.get("failure_reason") or None,
            failure_category=row.get("failure_category") or None,
            failure_timestamp=(
                datetime.fromisoformat(row["failure_timestamp"])
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

    return imported


async def _run_recovery_agent(db: AsyncSession, batch_id: str) -> dict:
    """Run the recovery agent on all eligible transactions."""
    from app.agent.recovery_agent import RecoveryAgent

    result = await db.execute(
        select(Transaction).where(
            Transaction.batch_id == batch_id,
            Transaction.status.in_(["failed", "abandoned", "overdue"]),
            Transaction.recovery_status.not_in(["recovered", "closed"]),
        )
    )
    transactions = list(result.scalars().all())

    agent_run_id = str(uuid.uuid4())
    batch_action_count = 0
    outcomes: dict[str, int] = {
        "succeeded": 0, "failed": 0, "blocked": 0,
        "human_review": 0, "other": 0,
    }

    for txn in transactions:
        try:
            agent = RecoveryAgent(
                db=db,
                agent_run_id=agent_run_id,
                batch_action_count=batch_action_count,
            )
            case = await agent.process_transaction(
                txn, auto_execute=True, batch_id=batch_id
            )
            batch_action_count = agent.batch_action_count
            state = case.state.lower()
            if state in outcomes:
                outcomes[state] += 1
            else:
                outcomes["other"] += 1
        except Exception as exc:
            logger.warning("Seed agent error", txn_id=txn.id, error=str(exc))
            outcomes["other"] += 1

    return {"processed": len(transactions), "outcomes": outcomes}


async def _run_evaluation(db: AsyncSession, batch_id: str) -> None:
    """Run 3-strategy evaluation so evaluation page is pre-populated."""
    from app.evaluation.evaluation_engine import EvaluationEngine
    try:
        engine = EvaluationEngine(db=db, seed=SEED)
        await engine.run_comparison(
            batch_id=batch_id,
            name_prefix="Auto-seed Evaluation",
        )
    except Exception as exc:
        logger.warning("Seed evaluation error", error=str(exc))


async def maybe_seed_demo_data(db: AsyncSession) -> bool:
    """
    Run the full demo seed if the database is empty.
    Returns True if seeding was performed, False if data already exists.
    """
    # Check if any transactions exist
    count_result = await db.execute(select(func.count()).select_from(Transaction))
    count = count_result.scalar_one()

    if count > 0:
        logger.info("Database already has data, skipping auto-seed", transaction_count=count)
        return False

    logger.info(
        "Empty database detected — running auto-seed",
        count=COUNT,
        seed=SEED,
    )

    try:
        batch_id = str(uuid.uuid4())

        # Step 1: Ensure merchant exists
        await _ensure_merchant(db)
        logger.info("Demo merchant ready")

        # Step 2: Import 100 synthetic transactions
        imported = await _import_transactions(db, batch_id)
        logger.info("Synthetic transactions imported", count=imported)

        # Step 3: Run recovery agent
        agent_result = await _run_recovery_agent(db, batch_id)
        logger.info("Recovery agent completed", **agent_result)

        # Step 4: Run 3-strategy evaluation
        await _run_evaluation(db, batch_id)
        logger.info("Evaluation completed")

        await db.commit()

        logger.info(
            "Auto-seed complete — dashboard is ready",
            transactions=imported,
            outcomes=agent_result["outcomes"],
        )
        return True

    except Exception as exc:
        logger.error("Auto-seed failed", error=str(exc))
        await db.rollback()
        return False
