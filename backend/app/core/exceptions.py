"""
Application-level exception classes and FastAPI error handlers.
"""
from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class RecoverAIException(Exception):
    """Base application exception."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(RecoverAIException):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(f"{resource} '{identifier}' not found", "NOT_FOUND")


class ValidationError(RecoverAIException):
    def __init__(self, message: str) -> None:
        super().__init__(message, "VALIDATION_ERROR")


class PolicyViolationError(RecoverAIException):
    def __init__(self, rule_id: str, reason: str) -> None:
        super().__init__(f"Policy violation [{rule_id}]: {reason}", "POLICY_VIOLATION")


class DuplicateActionError(RecoverAIException):
    def __init__(self, idempotency_key: str) -> None:
        super().__init__(
            f"Duplicate action prevented: {idempotency_key}", "DUPLICATE_ACTION"
        )


class AIProviderError(RecoverAIException):
    def __init__(self, message: str) -> None:
        super().__init__(message, "AI_PROVIDER_ERROR")


class PaymentProviderError(RecoverAIException):
    def __init__(self, message: str) -> None:
        super().__init__(message, "PAYMENT_PROVIDER_ERROR")


# ── FastAPI Exception Handlers ────────────────────────────────────────────────

async def recover_ai_exception_handler(
    request: Request, exc: RecoverAIException
) -> JSONResponse:
    status_map = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "POLICY_VIOLATION": status.HTTP_403_FORBIDDEN,
        "DUPLICATE_ACTION": status.HTTP_409_CONFLICT,
        "AI_PROVIDER_ERROR": status.HTTP_502_BAD_GATEWAY,
        "PAYMENT_PROVIDER_ERROR": status.HTTP_502_BAD_GATEWAY,
    }
    http_status = status_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    return JSONResponse(
        status_code=http_status,
        content={"error": exc.code, "message": exc.message},
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": exc.detail},
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
    )
