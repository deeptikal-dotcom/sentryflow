"""Agent management API — registration, suspension, revocation."""
from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user, require_role
from backend.audit.audit_logger import AuditLogger
from backend.database import get_session
from backend.models.agent import Agent
from backend.models.user import User
from backend.trust.crypto import generate_ed25519_keypair

router = APIRouter()
audit = AuditLogger()


def _parse_capabilities(raw) -> list[str]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            import ast
            return ast.literal_eval(raw)
    return []


class RegisterAgentRequest(BaseModel):
    name: str
    agent_type: str
    capabilities: list[str]


class AgentResponse(BaseModel):
    id: str
    name: str
    agent_type: str
    status: str
    capabilities: list[str]
    created_at: str


@router.get("/")
async def list_agents(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Agent).order_by(Agent.created_at.desc()))
    agents = result.scalars().all()
    return {
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "agent_type": a.agent_type,
                "status": a.status,
                "capabilities": _parse_capabilities(a.capabilities),
                "created_at": a.created_at,
            }
            for a in agents
        ]
    }


@router.post("/register")
async def register_agent(
    body: RegisterAgentRequest,
    user: Annotated[User, Depends(require_role("security_admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    existing = await session.execute(select(Agent).where(Agent.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Agent name already exists")

    priv, pub = generate_ed25519_keypair()
    now = datetime.now(UTC).isoformat()

    agent = Agent(
        id=str(uuid.uuid4()),
        name=body.name,
        agent_type=body.agent_type,
        public_key_ed25519=base64.b64encode(pub).decode("ascii"),
        capabilities=json.dumps(body.capabilities),
        status="active",
        registered_by=user.id,
        created_at=now,
        updated_at=now,
    )
    session.add(agent)

    await audit.log(
        session, "agent_registered", "user", user.id, f"register:{body.name}",
        target_type="agent", target_id=agent.id,
    )
    await session.commit()

    return {
        "id": agent.id,
        "name": agent.name,
        "public_key_ed25519": agent.public_key_ed25519,
        "private_key_ed25519": base64.b64encode(priv).decode("ascii"),
        "message": "Save the private key securely. It will not be shown again.",
    }


@router.post("/{agent_id}/suspend")
async def suspend_agent(
    agent_id: str,
    user: Annotated[User, Depends(require_role("security_admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = "suspended"
    agent.revoked_by = user.id
    agent.revoked_reason = "Suspended by admin"
    agent.updated_at = datetime.now(UTC).isoformat()

    await audit.log(
        session, "agent_suspended", "user", user.id, f"suspend:{agent.name}",
        target_type="agent", target_id=agent_id,
    )
    await session.commit()
    return {"id": agent_id, "status": "suspended"}


@router.post("/{agent_id}/revoke")
async def revoke_agent(
    agent_id: str,
    user: Annotated[User, Depends(require_role("security_admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = "revoked"
    agent.revoked_by = user.id
    agent.revoked_reason = "Revoked by admin"
    agent.updated_at = datetime.now(UTC).isoformat()

    await audit.log(
        session, "agent_revoked", "user", user.id, f"revoke:{agent.name}",
        target_type="agent", target_id=agent_id,
    )
    await session.commit()
    return {"id": agent_id, "status": "revoked"}


class RunAgentTaskRequest(BaseModel):
    agent_id: str
    task_description: str
    parameters: dict = {}


@router.post("/run-task")
async def run_agent_task(
    body: RunAgentTaskRequest,
    user: Annotated[User, Depends(require_role("security_admin", "procurement_operator"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Run an agent task using LLM (if available) or deterministic fallback."""
    result = await session.execute(
        select(Agent).where(Agent.id == body.agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.status != "active":
        raise HTTPException(status_code=403, detail=f"Agent is {agent.status}")

    from backend.agent_runner import AgentTask, process_task

    task = AgentTask(
        task_id=str(uuid.uuid4()),
        agent_type=agent.agent_type,
        agent_id=agent.id,
        description=body.task_description,
        parameters=body.parameters,
    )

    import os
    gateway_url = os.getenv("GATEWAY_URL", "http://localhost:8000")
    run_result = await process_task(task, gateway_url)

    await audit.log(
        session, "agent_task_run", "user", user.id,
        f"run_task:{agent.name}:{task.task_id}",
        target_type="agent", target_id=agent.id,
        decision_summary=f"llm={run_result.llm_used} success={run_result.success}",
    )
    await session.commit()

    return {
        "task_id": run_result.task_id,
        "agent_id": run_result.agent_id,
        "success": run_result.success,
        "tool_calls_made": run_result.tool_calls_made,
        "gateway_decisions": run_result.gateway_decisions,
        "llm_used": run_result.llm_used,
        "model": run_result.model,
        "total_latency_ms": run_result.total_latency_ms,
        "error": run_result.error,
    }
