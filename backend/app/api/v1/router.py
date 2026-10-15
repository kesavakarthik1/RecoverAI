"""API v1 router — aggregates all endpoint modules."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    dashboard,
    transactions,
    imports,
    recovery,
    evaluation,
    audit,
    policy,
    settings as settings_ep,
)

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(imports.router, prefix="/imports", tags=["Import & Batches"])
api_router.include_router(recovery.router, prefix="/recovery", tags=["Recovery Agent"])
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["Evaluation"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit Trail"])
api_router.include_router(policy.router, prefix="/policy", tags=["Policy"])
api_router.include_router(settings_ep.router, prefix="/settings", tags=["Settings"])
