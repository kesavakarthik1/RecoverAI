"""Batch Import — tracks CSV upload and processing state."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class BatchImport(Base, TimestampMixin):
    __tablename__ = "batch_imports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Status: uploading | validating | processing | completed | failed | partial
    status: Mapped[str] = mapped_column(String(50), default="uploading", nullable=False)

    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)

    # Validation errors (JSON list of {row, errors})
    validation_errors: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<BatchImport id={self.id} status={self.status} rows={self.total_rows}>"
