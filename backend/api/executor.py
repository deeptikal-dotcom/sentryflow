"""Executor API — execute authorized tool calls in the trusted zone.

Security guarantees:
- Only human users with appropriate roles can trigger execution
- The referenced ToolCall must exist and have been authorized by the gateway
- Financial tool calls require a valid, unconsumed approval
- The requesting agent must still be active at execution time
"""
from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user, require_role
from backend.audit.audit_logger import AuditLogger
from backend.database import get_session
from backend.executor.executor import Executor
from backend.models.agent import Agent
from backend.models.tool_call import ToolCall
from backend.models.user import User
from backend.trust.key_manager import get_executor_keys

router = APIRouter()
audit = AuditLogger()

EXECUTOR_ROLES = ("security_admin", "finance_approver", "procurement_operator")


class ExecuteRequest(BaseModel):
    tool_call_id: str
    tool_name: str
    parameters: dict[str, Any]
    approval_id: str | None = None


class ExecuteResponse(BaseModel):
    receipt_id: str
    tool_call_id: str
    tool_name: str
    status: str
    result: dict[str, Any] | None = None
    approval_id: str | None = None
    signature: str | None = None
    mldsa_signature: str | None = None
    pqc_signed: bool = False
    executed_at: str = ""
    error: str | None = None


@router.post("/run", response_model=ExecuteResponse)
async def execute_tool_call(
    body: ExecuteRequest,
    user: Annotated[User, Depends(require_role(*EXECUTOR_ROLES))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    tc_result = await session.execute(
        select(ToolCall).where(ToolCall.id == body.tool_call_id)
    )
    tc_record = tc_result.scalar_one_or_none()
    if tc_record is None:
        raise HTTPException(
            status_code=404,
            detail="ToolCall not found — execution requires prior gateway authorization",
        )

    if tc_record.policy_result == "deny":
        raise HTTPException(
            status_code=403,
            detail="ToolCall was denied by policy — cannot execute",
        )

    agent_result = await session.execute(
        select(Agent).where(Agent.id == tc_record.agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    if agent and agent.status in ("suspended", "revoked"):
        await audit.log(
            session, "execution_blocked", "executor", user.id,
            f"execute:{body.tool_name}",
            target_type="tool_call", target_id=body.tool_call_id,
            decision_summary=f"Agent {agent.status} at execution time",
            risk_score=100,
        )
        await session.commit()
        raise HTTPException(
            status_code=403,
            detail=f"Agent is {agent.status} — cannot execute authorized actions",
        )

    keys = get_executor_keys()
    executor = Executor(
        signing_key=keys.ed25519_private,
        mldsa_private_key=keys.mldsa_private,
    )
    receipt = await executor.execute(
        session,
        tool_call_id=body.tool_call_id,
        tool_name=body.tool_name,
        parameters=body.parameters,
        approval_id=body.approval_id,
        actor_id=user.id,
    )
    await session.commit()

    return ExecuteResponse(
        receipt_id=receipt.receipt_id,
        tool_call_id=receipt.tool_call_id,
        tool_name=receipt.tool_name,
        status=receipt.status,
        result=receipt.result or None,
        approval_id=receipt.approval_id,
        signature=receipt.signature,
        mldsa_signature=receipt.mldsa_signature,
        pqc_signed=receipt.pqc_signed,
        executed_at=receipt.executed_at,
        error=receipt.error,
    )
