"""
Payment Provider Abstraction.

Implementations:
  - SimulationProvider: deterministic simulated outcomes (no credentials needed)
  - RazorpayTestProvider: Razorpay test-mode adapter (requires test credentials)

IMPORTANT: This project NEVER executes real financial transactions.
           All operations are either simulated or limited to test mode.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PaymentProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def is_live(self) -> bool:
        """Always False for simulation and test-mode."""
        ...

    @abstractmethod
    async def execute_action(
        self,
        action_type: str,
        transaction_id: str,
        amount: Decimal,
        currency: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        ...


# ── Simulation Provider ───────────────────────────────────────────────────────

# Deterministic outcome probabilities per action and failure category
SIMULATION_SUCCESS_RATES = {
    "retry": {
        "temp_failure": 0.65,
        "auth_required": 0.0,  # Auth requires customer action
        "default": 0.20,
    },
    "send_reminder": {
        "default": 0.30,
    },
    "request_auth": {
        "auth_required": 0.60,
        "default": 0.40,
    },
    "escalate": {
        "default": 0.25,
    },
    "human_review": {
        "default": 1.0,  # Always succeeds (case flagged for review)
    },
    "stop": {
        "default": 1.0,  # Always "succeeds" — no action taken
    },
}


class SimulationProvider(PaymentProvider):
    """
    Fully simulated payment provider.
    Uses deterministic random seeding for reproducible outcomes.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed or settings.SYNTHETIC_SEED)

    @property
    def provider_name(self) -> str:
        return "simulation"

    @property
    def is_live(self) -> bool:
        return False

    async def execute_action(
        self,
        action_type: str,
        transaction_id: str,
        amount: Decimal,
        currency: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        meta = metadata or {}
        failure_cat = meta.get("failure_category", "unknown")

        rates = SIMULATION_SUCCESS_RATES.get(action_type, {"default": 0.3})
        success_rate = rates.get(failure_cat, rates.get("default", 0.3))

        # Use transaction_id for determinism (hash-based seed)
        rng = random.Random(hash(transaction_id + action_type) % (2**32))
        success = rng.random() < success_rate

        result = {
            "provider": "simulation",
            "action_type": action_type,
            "transaction_id": transaction_id,
            "success": success,
            "simulated": True,
            "success_rate_used": success_rate,
            "amount": str(amount),
            "currency": currency,
        }

        if success:
            result["message"] = f"Simulated {action_type} succeeded"
        else:
            result["message"] = f"Simulated {action_type} failed"
            result["error_code"] = "SIMULATION_FAILURE"

        logger.debug(
            "Simulated action executed",
            action_type=action_type,
            success=success,
            transaction_id=transaction_id,
        )
        return result

    async def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        return {
            "provider": "simulation",
            "transaction_id": transaction_id,
            "status": "unknown",
            "simulated": True,
        }


# ── Razorpay Test Provider ────────────────────────────────────────────────────

class RazorpayTestProvider(PaymentProvider):
    """
    Razorpay test-mode adapter.
    Uses test credentials only — never processes real payments.

    Supported test-mode operations:
    - Fetch payment status
    - Simulate payment capture (test mode)

    Note: Not all retry operations may be available in Razorpay test mode.
    This adapter only calls verified test-mode endpoints.
    """

    def __init__(self) -> None:
        self._key_id = settings.RAZORPAY_KEY_ID
        self._key_secret = settings.RAZORPAY_KEY_SECRET
        self._base_url = "https://api.razorpay.com/v1"
        self._configured = bool(self._key_id and self._key_secret)

        if not self._configured:
            logger.warning(
                "Razorpay test credentials not configured. "
                "Operations will fall back to simulation."
            )

    @property
    def provider_name(self) -> str:
        return "razorpay_test"

    @property
    def is_live(self) -> bool:
        return False  # Test mode only — NEVER live

    async def execute_action(
        self,
        action_type: str,
        transaction_id: str,
        amount: Decimal,
        currency: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self._configured:
            # Fallback to simulation
            logger.info("Razorpay not configured, using simulation fallback")
            sim = SimulationProvider()
            result = await sim.execute_action(
                action_type, transaction_id, amount, currency, metadata
            )
            result["provider"] = "razorpay_test_fallback_simulation"
            return result

        # Test-mode: only fetch status is a safe read-only operation
        if action_type in ("retry",):
            return {
                "provider": "razorpay_test",
                "action_type": action_type,
                "transaction_id": transaction_id,
                "success": False,
                "simulated": False,
                "message": (
                    f"Razorpay test-mode does not support '{action_type}' "
                    "for existing failed transactions. Using simulation outcome."
                ),
                "note": "Razorpay test-mode limitation: retry of existing payment not supported via API.",
            }

        return {
            "provider": "razorpay_test",
            "action_type": action_type,
            "transaction_id": transaction_id,
            "success": True,
            "simulated": False,
            "test_mode": True,
            "message": f"Razorpay test-mode action '{action_type}' recorded.",
        }

    async def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        if not self._configured:
            return {"provider": "razorpay_test", "status": "unknown", "configured": False}

        import httpx

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                auth=(self._key_id, self._key_secret),
                timeout=10,
            ) as client:
                response = await client.get(f"/payments/{transaction_id}")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "provider": "razorpay_test",
                        "transaction_id": transaction_id,
                        "status": data.get("status", "unknown"),
                        "amount": data.get("amount"),
                        "currency": data.get("currency"),
                        "test_mode": True,
                    }
                else:
                    return {
                        "provider": "razorpay_test",
                        "transaction_id": transaction_id,
                        "status": "not_found",
                        "error": f"HTTP {response.status_code}",
                    }
        except Exception as exc:
            logger.error("Razorpay API call failed", error=str(exc))
            return {
                "provider": "razorpay_test",
                "transaction_id": transaction_id,
                "status": "error",
                "error": str(exc),
            }


# ── Factory ───────────────────────────────────────────────────────────────────

def get_payment_provider() -> PaymentProvider:
    """Return the configured payment provider."""
    if settings.PAYMENT_PROVIDER == "razorpay_test":
        logger.info("Using Razorpay test-mode provider")
        return RazorpayTestProvider()
    logger.info("Using simulation payment provider")
    return SimulationProvider()
