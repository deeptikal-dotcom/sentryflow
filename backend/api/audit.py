"""Audit trail API — event listing, chain verification."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user, require_role
from backend.audit.audit_logger import AuditLogger
from backend.database import get_session
from backend.models.audit import AuditLog
from backend.models.user import User

router = APIRouter()
audit = AuditLogger()


@router.get("/events")
async def list_events(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=50, le=500),
):
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.sequence_num.desc()).limit(limit)
    )
    events = result.scalars().all()
    return {
        "events": [
            {
                "sequence_num": e.sequence_num,
                "event_type": e.event_type,
                "actor_type": e.actor_type,
                "actor_id": e.actor_id,
                "action": e.action,
                "target_type": e.target_type,
                "target_id": e.target_id,
                "risk_score": e.risk_score,
                "created_at": e.created_at,
            }
            for e in events
        ]
    }


@router.get("/verify")
async def verify_chain(
    user: Annotated[User, Depends(require_role("auditor", "security_admin", "security_analyst"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    is_valid, errors = await audit.verify_chain(session)
    return {"valid": is_valid, "errors": errors}


@router.get("/stats")
async def audit_stats(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    total_result = await session.execute(select(func.count(AuditLog.id)))
    total = total_result.scalar() or 0
    return {"total_events": total}
