"""Executor API — execute authorized tool calls in the trusted zone."""
from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user, require_role
from backend.audit.audit_logger import AuditLogger
from backend.database import get_session
from backend.executor.executor import Executor
from backend.models.user import User

router = APIRouter()
audit = AuditLogger()


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
    executed_at: str = ""
    error: str | None = None


@router.post("/run", response_model=ExecuteResponse)
async def execute_tool_call(
    body: ExecuteRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    executor = Executor()
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
        executed_at=receipt.executed_at,
        error=receipt.error,
    )
