"""Audit trail endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.schemas.audit import AuditEventRead
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[AuditEventRead])
async def list_audit_events(
    transaction_id: Optional[str] = None,
    recovery_case_id: Optional[str] = None,
    batch_id: Optional[str] = None,
    event_type: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AuditEventRead]:
    query = select(AuditEvent)

    if transaction_id:
        query = query.where(AuditEvent.transaction_id == transaction_id)
    if recovery_case_id:
        query = query.where(AuditEvent.recovery_case_id == recovery_case_id)
    if batch_id:
        query = query.where(AuditEvent.batch_id == batch_id)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type.upper())

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(page_size)
    )
    events = result.scalars().all()

    return PaginatedResponse(
        items=[AuditEventRead.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )
