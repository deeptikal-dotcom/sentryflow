"""Approval workflow API — human-in-the-loop authorization."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.audit.audit_logger import AuditLogger
from backend.database import get_session
from backend.models.approval import Approval
from backend.models.user import User
from backend.trust.approval_manager import ApprovalError, ApprovalManager

router = APIRouter()
approval_mgr = ApprovalManager()
audit = AuditLogger()


class DecisionRequest(BaseModel):
    decision: str  # approved|denied
    reason: str | None = None


@router.get("/pending")
async def list_pending(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Approval)
        .where(Approval.decision == "pending")
        .where(Approval.required_role == user.role)
        .order_by(Approval.created_at.desc())
    )
    approvals = result.scalars().all()
    return {
        "approvals": [
            {
                "id": a.id,
                "tool_call_id": a.tool_call_id,
                "requesting_agent_id": a.requesting_agent_id,
                "canonical_params": a.canonical_params,
                "required_role": a.required_role,
                "expires_at": a.expires_at,
                "created_at": a.created_at,
            }
            for a in approvals
        ]
    }


@router.post("/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    body: DecisionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    if body.decision not in ("approved", "denied"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'denied'")

    try:
        approval = await approval_mgr.decide(
            session, approval_id, user.id, user.role, body.decision, body.reason
        )
    except ApprovalError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await audit.log(
        session,
        event_type="approval_decided",
        actor_type="user",
        actor_id=user.id,
        action=f"approval:{body.decision}",
        target_type="approval",
        target_id=approval_id,
        decision_summary=f"{body.decision}: {body.reason or 'No reason provided'}",
    )
    await session.commit()

    return {
        "id": approval.id,
        "decision": approval.decision,
        "approver_id": approval.approver_id,
        "resolved_at": approval.resolved_at,
    }


@router.get("/history")
async def approval_history(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 50,
):
    result = await session.execute(
        select(Approval)
        .where(Approval.decision != "pending")
        .order_by(Approval.created_at.desc())
        .limit(limit)
    )
    approvals = result.scalars().all()
    return {
        "approvals": [
            {
                "id": a.id,
                "tool_call_id": a.tool_call_id,
                "decision": a.decision,
                "approver_id": a.approver_id,
                "consumed": a.consumed,
                "created_at": a.created_at,
                "resolved_at": a.resolved_at,
            }
            for a in approvals
        ]
    }
