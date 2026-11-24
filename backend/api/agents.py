"""Agent management API — registration, suspension, revocation."""
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
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
                "capabilities": json.loads(a.capabilities) if isinstance(a.capabilities, str) else a.capabilities,
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
    now = datetime.now(timezone.utc).isoformat()

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
    agent.updated_at = datetime.now(timezone.utc).isoformat()

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
    agent.updated_at = datetime.now(timezone.utc).isoformat()

    await audit.log(
        session, "agent_revoked", "user", user.id, f"revoke:{agent.name}",
        target_type="agent", target_id=agent_id,
    )
    await session.commit()
    return {"id": agent_id, "status": "revoked"}
