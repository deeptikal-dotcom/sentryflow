from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/events")
async def list_events():
    return {"events": [], "message": "Audit trail - implementation pending"}
