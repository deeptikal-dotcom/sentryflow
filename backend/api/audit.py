"""Audit trail API — event listing, chain verification, checkpoints, export."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user, require_role
from backend.audit.audit_logger import AuditLogger
from backend.database import get_session
from backend.models.audit import AuditCheckpoint, AuditLog
from backend.models.user import User
from backend.trust.key_manager import get_executor_keys

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

    cp_count_result = await session.execute(select(func.count(AuditCheckpoint.id)))
    cp_count = cp_count_result.scalar() or 0

    last_cp_result = await session.execute(
        select(AuditCheckpoint).order_by(AuditCheckpoint.sequence_to.desc()).limit(1)
    )
    last_cp = last_cp_result.scalar_one_or_none()

    return {
        "total_events": total,
        "checkpoints": cp_count,
        "last_checkpoint_at": last_cp.created_at if last_cp else None,
        "last_checkpoint_seq": last_cp.sequence_to if last_cp else None,
    }


@router.post("/checkpoint")
async def create_checkpoint(
    user: Annotated[User, Depends(require_role("auditor", "security_admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    keys = get_executor_keys()
    cp = await audit.create_checkpoint(
        session,
        signing_key=keys.ed25519_private,
        mldsa_key=keys.mldsa_private,
    )
    if cp is None:
        return {"created": False, "reason": "No new records since last checkpoint"}
    await session.commit()
    return {
        "created": True,
        "checkpoint_id": cp.id,
        "sequence_from": cp.sequence_from,
        "sequence_to": cp.sequence_to,
        "record_count": cp.record_count,
        "pqc_signed": cp.signature_mldsa is not None,
    }


@router.get("/checkpoints")
async def list_checkpoints(
    user: Annotated[User, Depends(require_role("auditor", "security_admin", "security_analyst"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(AuditCheckpoint).order_by(AuditCheckpoint.sequence_to.desc())
    )
    cps = result.scalars().all()
    return {
        "checkpoints": [
            {
                "id": cp.id,
                "sequence_from": cp.sequence_from,
                "sequence_to": cp.sequence_to,
                "record_count": cp.record_count,
                "chain_hash": cp.chain_hash,
                "pqc_signed": cp.signature_mldsa is not None,
                "created_at": cp.created_at,
            }
            for cp in cps
        ]
    }


@router.get("/export/{checkpoint_id}")
async def export_checkpoint(
    checkpoint_id: str,
    user: Annotated[User, Depends(require_role("auditor", "security_admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        data = await audit.export_checkpoint(session, checkpoint_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return data
