"""Security Gateway API — the central interception point for all agent actions.

Every agent tool call passes through this gateway. The gateway:
1. Validates agent identity and capabilities
2. Scans for prompt injection in context
3. Evaluates the deterministic policy engine
4. Routes to approval workflows if escalation required
5. Logs all decisions to the audit trail
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.audit.audit_logger import AuditLogger
from backend.database import get_session
from backend.models.agent import Agent
from backend.models.policy import PolicyVersion
from backend.models.tool_call import ToolCall
from backend.models.user import User
from backend.security.injection_detector import InjectionDetector
from backend.executor.executor import Executor
from backend.trust.approval_manager import ApprovalManager
from backend.trust.crypto import canonical_hash, canonical_json
from backend.trust.policy_engine import PolicyDecision, PolicyEngine, ToolCallContext

router = APIRouter()
detector = InjectionDetector()
approval_mgr = ApprovalManager()
audit = AuditLogger()


class ToolCallRequest(BaseModel):
    agent_id: str
    tool_name: str
    parameters: dict[str, Any]
    context: str | None = None
    session_id: str = ""
    auto_execute: bool = False


class ExecutionResult(BaseModel):
    receipt_id: str = ""
    status: str = ""
    result: dict[str, Any] | None = None
    signature: str | None = None
    mldsa_signature: str | None = None
    pqc_signed: bool = False
    error: str | None = None


class ToolCallResponse(BaseModel):
    tool_call_id: str
    decision: str
    risk_score: int
    approval_required: bool = False
    approval_id: str | None = None
    required_role: str | None = None
    reason: str | None = None
    rule_trace: list[dict] | None = None
    execution: ExecutionResult | None = None


@router.post("/evaluate", response_model=ToolCallResponse)
async def evaluate_tool_call(
    body: ToolCallRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Agent).where(Agent.id == body.agent_id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.status in ("suspended", "revoked"):
        await audit.log(
            session, "action_denied", "agent", agent.id,
            f"tool_call:{body.tool_name}",
            decision_summary=f"Agent {agent.status}",
            risk_score=100,
        )
        await session.commit()
        raise HTTPException(status_code=403, detail=f"Agent is {agent.status}")

    injection_score = 0
    if body.context:
        scan = detector.scan(body.context)
        injection_score = scan.score

    capabilities = json.loads(agent.capabilities) if isinstance(agent.capabilities, str) else agent.capabilities
    classification = _classify_tool(body.tool_name, body.parameters)

    ctx = ToolCallContext(
        agent_id=body.agent_id,
        agent_status=agent.status,
        agent_capabilities=capabilities,
        tool_name=body.tool_name,
        classification=classification,
        parameters=body.parameters,
        amount_minor=body.parameters.get("amount_minor"),
        injection_score=injection_score,
        session_id=body.session_id,
    )

    engine = PolicyEngine()
    policy_result = engine.evaluate(ctx)

    tc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    policy_version_id = await _ensure_policy_version(
        session, engine, user.id
    )

    tc_record = ToolCall(
        id=tc_id,
        agent_id=body.agent_id,
        session_id=body.session_id or "default",
        tool_name=body.tool_name,
        parameters_hash=canonical_hash(body.parameters),
        parameters_encrypted=json.dumps(body.parameters),
        classification=classification,
        injection_context=json.dumps({"score": injection_score}) if injection_score > 0 else None,
        policy_version_id=policy_version_id,
        policy_result=policy_result.decision.value,
        policy_rule_trace=json.dumps(policy_result.rule_trace) if policy_result.rule_trace else None,
        risk_score=policy_result.risk_score,
        status=policy_result.decision.value,
        created_at=now,
    )
    session.add(tc_record)
    await session.flush()

    response = ToolCallResponse(
        tool_call_id=tc_id,
        decision=policy_result.decision.value,
        risk_score=policy_result.risk_score,
        reason=policy_result.reason,
        rule_trace=policy_result.rule_trace,
    )

    if policy_result.decision == PolicyDecision.ESCALATE:
        approval = await approval_mgr.create_approval_request(
            session,
            tool_call_id=tc_id,
            parameters=body.parameters,
            requesting_agent_id=body.agent_id,
            required_role=policy_result.required_role or "finance_approver",
            policy_version_id=policy_version_id,
        )
        response.approval_required = True
        response.approval_id = approval.id
        response.required_role = policy_result.required_role

    await audit.log(
        session, "action_decided", "agent", body.agent_id,
        f"tool_call:{body.tool_name}",
        target_type="tool_call",
        target_id=tc_id,
        decision_summary=f"{policy_result.decision.value}: {policy_result.reason or policy_result.matched_rule_id}",
        rule_trace=policy_result.rule_trace,
        risk_score=policy_result.risk_score,
    )

    if body.auto_execute and policy_result.decision == PolicyDecision.ALLOW:
        from backend.trust.key_manager import get_executor_keys
        keys = get_executor_keys()
        executor = Executor(
            signing_key=keys.ed25519_private,
            mldsa_private_key=keys.mldsa_private,
        )
        receipt = await executor.execute(
            session,
            tool_call_id=tc_id,
            tool_name=body.tool_name,
            parameters=body.parameters,
            actor_id=body.agent_id,
        )
        response.execution = ExecutionResult(
            receipt_id=receipt.receipt_id,
            status=receipt.status,
            result=receipt.result or None,
            signature=receipt.signature,
            mldsa_signature=receipt.mldsa_signature,
            pqc_signed=receipt.pqc_signed,
            error=receipt.error,
        )

    await session.commit()

    return response


@router.get("/policies")
async def list_policies(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(PolicyVersion).where(PolicyVersion.active == True).order_by(PolicyVersion.version.desc())
    )
    policies = result.scalars().all()
    return {
        "policies": [
            {
                "id": p.id,
                "version": p.version,
                "name": p.name,
                "content_hash": p.content_hash,
                "active": p.active,
                "created_at": p.created_at,
            }
            for p in policies
        ]
    }


async def _ensure_policy_version(
    session: AsyncSession, engine: PolicyEngine, created_by: str
) -> str:
    content_hash = engine.content_hash
    result = await session.execute(
        select(PolicyVersion).where(PolicyVersion.content_hash == content_hash)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing.id

    from pathlib import Path
    pv_id = str(uuid.uuid4())
    rules_path = Path(__file__).parent.parent.parent / "data" / "policies" / "default.yaml"
    rules_text = rules_path.read_text() if rules_path.exists() else ""
    pv = PolicyVersion(
        id=pv_id,
        version=engine.version,
        name=engine.name,
        rules_yaml=rules_text,
        content_hash=content_hash,
        created_by=created_by,
        active=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    session.add(pv)
    await session.flush()
    return pv_id


def _classify_tool(tool_name: str, params: dict) -> str:
    financial_tools = {
        "create_payment", "approve_payment", "execute_payment",
        "update_bank_details", "modify_payment",
    }
    critical_tools = {
        "modify_policy", "revoke_agent", "suspend_agent",
        "delete_supplier", "modify_audit",
    }
    write_tools = {
        "create_purchase_order", "update_po_status", "receive_goods",
        "process_invoice", "register_supplier", "update_supplier",
    }

    if tool_name in financial_tools:
        return "financial"
    if tool_name in critical_tools:
        return "critical"
    if tool_name in write_tools:
        return "write"
    return "read_only"
