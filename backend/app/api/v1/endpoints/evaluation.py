"""Evaluation and strategy comparison endpoints."""
from __future__ import annotations

import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.evaluation.evaluation_engine import EvaluationEngine
from app.models.evaluation_run import EvaluationRun
from app.models.evaluation_result import EvaluationResult
from app.schemas.evaluation import EvaluationRunRead, StrategyComparisonResponse

router = APIRouter()


@router.post("/run")
async def run_evaluation(
    batch_id: Optional[str] = None,
    seed: int = 42,
    name: str = "Evaluation Run",
    db: AsyncSession = Depends(get_db),
):
    """
    Run all three recovery strategy evaluations on the given batch.
    Returns metric comparison across baseline, fixed_rule, ai_assisted.
    """
    engine = EvaluationEngine(db=db, seed=seed)
    runs = await engine.run_comparison(
        batch_id=batch_id,
        name_prefix=name,
    )

    return {
        "evaluation_runs": {
            strategy: {
                "id": run.id,
                "strategy": run.strategy,
                "status": run.status,
                "total_transaction_count": run.total_transaction_count,
                "eligible_at_risk_count": run.eligible_at_risk_count,
                "total_revenue_at_risk": float(run.total_revenue_at_risk),
                "estimated_recoverable_value": float(run.estimated_recoverable_value),
                "successful_recoveries": run.successful_recoveries,
                "simulated_recovered_value": float(run.simulated_recovered_value),
                "recovery_rate_by_count": float(run.recovery_rate_by_count or 0),
                "recovery_rate_by_value": float(run.recovery_rate_by_value or 0),
                "blocked_action_count": run.blocked_action_count,
                "human_review_count": run.human_review_count,
                "estimated_intervention_cost": float(run.estimated_intervention_cost),
                "net_simulated_recovery_value": float(run.net_simulated_recovery_value),
                "false_positive_intervention_count": run.false_positive_intervention_count,
                "precision": float(run.precision) if run.precision else None,
                "recall": float(run.recall) if run.recall else None,
                "results_by_category": run.results_by_category,
            }
            for strategy, run in runs.items()
        }
    }


@router.get("/runs")
async def list_evaluation_runs(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(20)
    )
    runs = result.scalars().all()
    return [EvaluationRunRead.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=EvaluationRunRead)
async def get_evaluation_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EvaluationRun).where(EvaluationRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise NotFoundError("EvaluationRun", run_id)
    return EvaluationRunRead.model_validate(run)


@router.get("/compare")
async def compare_strategies(
    batch_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Return the latest run of each strategy for comparison."""
    strategies = ["baseline", "fixed_rule", "ai_assisted"]
    comparison = {}

    for strategy in strategies:
        query = select(EvaluationRun).where(
            EvaluationRun.strategy == strategy,
            EvaluationRun.status == "completed",
        )
        if batch_id:
            query = query.where(EvaluationRun.batch_id == batch_id)
        result = await db.execute(
            query.order_by(EvaluationRun.created_at.desc()).limit(1)
        )
        run = result.scalar_one_or_none()
        if run:
            comparison[strategy] = EvaluationRunRead.model_validate(run)

    # Build comparison table
    metrics = [
        "total_transaction_count",
        "eligible_at_risk_count",
        "total_revenue_at_risk",
        "successful_recoveries",
        "simulated_recovered_value",
        "recovery_rate_by_count",
        "recovery_rate_by_value",
        "blocked_action_count",
        "human_review_count",
        "estimated_intervention_cost",
        "net_simulated_recovery_value",
        "false_positive_intervention_count",
    ]

    table = []
    for metric in metrics:
        row = {"metric": metric}
        for strategy, run in comparison.items():
            val = getattr(run, metric, None)
            row[strategy] = float(val) if val is not None else None
        table.append(row)

    return {
        "strategies": comparison,
        "comparison_table": table,
    }


@router.get("/runs/{run_id}/export")
async def export_evaluation_report(
    run_id: str,
    format: str = Query(default="csv", regex="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
):
    """Export evaluation run results as CSV or JSON."""
    run_result = await db.execute(
        select(EvaluationRun).where(EvaluationRun.id == run_id)
    )
    run = run_result.scalar_one_or_none()
    if not run:
        raise NotFoundError("EvaluationRun", run_id)

    results_result = await db.execute(
        select(EvaluationResult).where(EvaluationResult.evaluation_run_id == run_id)
    )
    results = results_result.scalars().all()

    if format == "json":
        export_data = {
            "run": {
                "id": run.id,
                "name": run.name,
                "strategy": run.strategy,
                "status": run.status,
                "metrics": {
                    "total_transaction_count": run.total_transaction_count,
                    "eligible_at_risk_count": run.eligible_at_risk_count,
                    "total_revenue_at_risk": float(run.total_revenue_at_risk),
                    "successful_recoveries": run.successful_recoveries,
                    "simulated_recovered_value": float(run.simulated_recovered_value),
                    "recovery_rate_by_count": float(run.recovery_rate_by_count or 0),
                    "recovery_rate_by_value": float(run.recovery_rate_by_value or 0),
                    "net_simulated_recovery_value": float(run.net_simulated_recovery_value),
                    "results_by_category": run.results_by_category,
                },
            },
            "transaction_results": [
                {
                    "transaction_id": r.transaction_id,
                    "ground_truth_recoverable": r.ground_truth_recoverable,
                    "predicted_recoverable": r.predicted_recoverable,
                    "action_taken": r.action_taken,
                    "action_blocked": r.action_blocked,
                    "recovery_succeeded": r.recovery_succeeded,
                    "recovered_amount": float(r.recovered_amount),
                    "at_risk_amount": float(r.at_risk_amount),
                    "intervention_cost": float(r.intervention_cost),
                    "is_true_positive": r.is_true_positive,
                    "is_false_positive": r.is_false_positive,
                }
                for r in results
            ],
        }
        content = json.dumps(export_data, indent=2, default=str)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=evaluation_{run_id}.json"},
        )

    # CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "transaction_id", "ground_truth_recoverable", "predicted_recoverable",
        "action_taken", "action_blocked", "block_reason", "recovery_succeeded",
        "recovered_amount", "at_risk_amount", "intervention_cost",
        "is_true_positive", "is_false_positive", "risk_score",
    ])
    for r in results:
        writer.writerow([
            r.transaction_id,
            r.ground_truth_recoverable,
            r.predicted_recoverable,
            r.action_taken,
            r.action_blocked,
            r.block_reason,
            r.recovery_succeeded,
            float(r.recovered_amount),
            float(r.at_risk_amount),
            float(r.intervention_cost),
            r.is_true_positive,
            r.is_false_positive,
            float(r.risk_score) if r.risk_score else None,
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=evaluation_{run_id}.csv"},
    )
