"""Incident management API."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.database import get_session
from backend.models.incident import Incident
from backend.models.user import User

router = APIRouter()


@router.get("/")
async def list_incidents(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Incident).order_by(Incident.detected_at.desc())
    )
    incidents = result.scalars().all()
    return {
        "incidents": [
            {
                "id": i.id,
                "incident_type": i.incident_type,
                "severity": i.severity,
                "title": i.title,
                "description": i.description,
                "status": i.status,
                "detected_at": i.detected_at,
                "source_agent_id": i.source_agent_id,
            }
            for i in incidents
        ]
    }
