"""Application settings endpoint — read-only, no secrets exposed."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("")
async def get_app_settings():
    """Return safe, non-secret application configuration."""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "ai_provider": settings.AI_PROVIDER,
        "payment_provider": settings.PAYMENT_PROVIDER,
        "is_live_payment": False,  # Always false — no real payments
        "default_currency": "INR",
        "max_retry_attempts": settings.MAX_RETRY_ATTEMPTS,
        "min_retry_delay_hours": settings.MIN_RETRY_DELAY_HOURS,
        "approval_threshold_inr": settings.APPROVAL_THRESHOLD_INR,
        "synthetic_seed": settings.SYNTHETIC_SEED,
        "llm_configured": bool(settings.OPENROUTER_API_KEY),
        "razorpay_configured": bool(settings.RAZORPAY_KEY_ID),
    }
