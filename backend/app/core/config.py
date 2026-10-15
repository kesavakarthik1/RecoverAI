"""
Application configuration management.
All settings are loaded from environment variables with safe defaults.
"""
from __future__ import annotations

import secrets
from typing import Literal, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "RecoverAI"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    SECRET_KEY: str = secrets.token_urlsafe(32)
    API_V1_STR: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./recoverai.db"
    DATABASE_ECHO: bool = False
    # Sync URL used by Alembic (which is synchronous)
    SYNC_DATABASE_URL: str = "sqlite:///./recoverai.db"

    # ── CORS ──────────────────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # ── AI Provider ───────────────────────────────────────────────────────────
    AI_PROVIDER: Literal["rule_based", "openrouter"] = "rule_based"
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    AI_REQUEST_TIMEOUT_SECONDS: int = 30
    AI_MAX_RETRIES: int = 2

    # ── Payment Provider ──────────────────────────────────────────────────────
    PAYMENT_PROVIDER: Literal["simulation", "razorpay_test"] = "simulation"
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None

    # ── Recovery Policy Defaults ──────────────────────────────────────────────
    MAX_RETRY_ATTEMPTS: int = 3
    MIN_RETRY_DELAY_HOURS: int = 24
    MAX_RECOVERY_ACTIONS_PER_TXN: int = 5
    MAX_REMINDERS_PER_CUSTOMER_PER_WEEK: int = 2
    APPROVAL_THRESHOLD_INR: int = 50000  # Require human approval above this amount
    BATCH_MAX_ACTIONS: int = 500

    # ── File Upload ────────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_UPLOAD_EXTENSIONS: list[str] = [".csv"]

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "console"

    # ── Synthetic Data ────────────────────────────────────────────────────────
    SYNTHETIC_SEED: int = 42
    SYNTHETIC_DEFAULT_COUNT: int = 100

    # ── Auto-seed demo data on first startup ──────────────────────────────────
    # Disable with AUTO_SEED_DEMO_DATA=false in .env for production deployments
    # or when you want to start with a clean database.
    AUTO_SEED_DEMO_DATA: bool = True

    @model_validator(mode="after")
    def _set_sync_url_from_async(self) -> "Settings":
        """Derive a synchronous DB URL from the async one for Alembic."""
        if self.DATABASE_URL.startswith("sqlite+aiosqlite"):
            object.__setattr__(
                self,
                "SYNC_DATABASE_URL",
                self.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite"),
            )
        elif self.DATABASE_URL.startswith("postgresql+asyncpg"):
            object.__setattr__(
                self,
                "SYNC_DATABASE_URL",
                self.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
            )
        return self


settings = Settings()
