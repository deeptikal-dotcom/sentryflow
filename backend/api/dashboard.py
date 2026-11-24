"""Dashboard API — security posture overview and metrics."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.database import get_session
from backend.models.agent import Agent
from backend.models.approval import Approval
from backend.models.audit import AuditLog
from backend.models.incident import Incident
from backend.models.invoice import Invoice
from backend.models.supplier import Supplier
from backend.models.user import User
from backend.trust.crypto import detect_pqc_capabilities

router = APIRouter()


@router.get("/overview")
async def overview(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    agents_active = (await session.execute(
        select(func.count()).select_from(Agent).where(Agent.status == "active")
    )).scalar() or 0

    agents_total = (await session.execute(
        select(func.count()).select_from(Agent)
    )).scalar() or 0

    approvals_pending = (await session.execute(
        select(func.count()).select_from(Approval).where(Approval.decision == "pending")
    )).scalar() or 0

    incidents_open = (await session.execute(
        select(func.count()).select_from(Incident)
        .where(Incident.status.in_(["detected", "investigating"]))
    )).scalar() or 0

    suppliers_verified = (await session.execute(
        select(func.count()).select_from(Supplier).where(Supplier.verified == True)
    )).scalar() or 0

    suppliers_total = (await session.execute(
        select(func.count()).select_from(Supplier)
    )).scalar() or 0

    invoices_processing = (await session.execute(
        select(func.count()).select_from(Invoice)
        .where(Invoice.status.in_(["received", "processing"]))
    )).scalar() or 0

    invoices_suspicious = (await session.execute(
        select(func.count()).select_from(Invoice)
        .where(Invoice.validation_status == "suspicious")
    )).scalar() or 0

    audit_count = (await session.execute(
        select(func.count()).select_from(AuditLog)
    )).scalar() or 0

    pqc = detect_pqc_capabilities()

    return {
        "status": "operational",
        "agents": {"active": agents_active, "total": agents_total},
        "approvals": {"pending": approvals_pending},
        "incidents": {"open": incidents_open},
        "suppliers": {"verified": suppliers_verified, "total": suppliers_total},
        "invoices": {"processing": invoices_processing, "suspicious": invoices_suspicious},
        "audit": {"total_events": audit_count},
        "crypto": {
            "mldsa_available": pqc.mldsa_available,
            "mlkem_available": pqc.mlkem_available,
            "openssl_version": pqc.openssl_version,
        },
    }


@router.get("/recent-activity")
async def recent_activity(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 20,
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
                "risk_score": e.risk_score,
                "created_at": e.created_at,
            }
            for e in events
        ]
    }
