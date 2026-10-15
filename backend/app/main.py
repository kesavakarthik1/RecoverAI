"""
RecoverAI — FastAPI Application Entry Point
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import init_db, AsyncSessionLocal
from app.core.exceptions import (
    RecoverAIException,
    recover_ai_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)
from app.core.logging import configure_logging, get_logger
from app.api.v1.router import api_router
from app.services.seed_data import maybe_seed_demo_data

configure_logging()
logger = get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    logger.info(
        "Starting RecoverAI",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        ai_provider=settings.AI_PROVIDER,
        payment_provider=settings.PAYMENT_PROVIDER,
    )

    # 1. Create all DB tables
    await init_db()
    logger.info("Database initialised")

    # 2. Auto-seed demo data if DB is empty (first run)
    if settings.AUTO_SEED_DEMO_DATA:
        async with AsyncSessionLocal() as db:
            seeded = await maybe_seed_demo_data(db)
            if seeded:
                logger.info(
                    "Demo data seeded — dashboard is ready with 100 synthetic transactions"
                )
    else:
        logger.info("Auto-seed disabled (AUTO_SEED_DEMO_DATA=false)")

    yield
    logger.info("RecoverAI shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-Powered Revenue Recovery Agent — "
        "Razorpay AI Buildathon submission"
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Exception Handlers ────────────────────────────────────────────────────────

app.add_exception_handler(RecoverAIException, recover_ai_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "ai_provider": settings.AI_PROVIDER,
        "payment_provider": settings.PAYMENT_PROVIDER,
    }


@app.get("/", tags=["Root"])
async def root() -> dict:
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
    }
