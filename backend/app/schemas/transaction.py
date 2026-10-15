"""Transaction Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TransactionRead(BaseModel):
    id: str
    external_id: Optional[str] = None
    batch_id: Optional[str] = None
    merchant_id: str
    customer_ref: str
    amount: Decimal
    currency: str
    transaction_type: str
    status: str
    failure_reason: Optional[str] = None
    failure_category: Optional[str] = None
    failure_timestamp: Optional[datetime] = None
    retry_count: int
    risk_score: Optional[Decimal] = None
    recoverability: str
    recovery_status: str
    payment_method: Optional[str] = None
    gateway: Optional[str] = None
    is_synthetic: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionList(BaseModel):
    id: str
    external_id: Optional[str] = None
    customer_ref: str
    amount: Decimal
    currency: str
    transaction_type: str
    status: str
    failure_category: Optional[str] = None
    retry_count: int
    risk_score: Optional[Decimal] = None
    recoverability: str
    recovery_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionFilter(BaseModel):
    status: Optional[str] = None
    recovery_status: Optional[str] = None
    failure_category: Optional[str] = None
    transaction_type: Optional[str] = None
    merchant_id: Optional[str] = None
    batch_id: Optional[str] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
