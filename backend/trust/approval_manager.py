"""Nonce-bound, parameter-canonical approval workflows.

Implements SI-5 (approval binds exact parameters), SI-6 (modified/replayed
approvals rejected), and SI-7 (high-risk actions require human auth).
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.approval import Approval
from backend.trust.crypto import canonical_hash, canonical_json


class ApprovalError(Exception):
    pass


class ApprovalManager:
    def __init__(self, default_expiry_minutes: int = 30, max_escalation: int = 2):
        self._default_expiry = default_expiry_minutes
        self._max_escalation = max_escalation

    async def create_approval_request(
        self,
        session: AsyncSession,
        tool_call_id: str,
        parameters: dict,
        requesting_agent_id: str,
        required_role: str,
        policy_version_id: str,
    ) -> Approval:
        canonical = canonical_json(parameters).decode("utf-8")
        c_hash = canonical_hash(parameters)
        now = datetime.now(timezone.utc)

        approval = Approval(
            id=str(uuid.uuid4()),
            tool_call_id=tool_call_id,
            nonce=secrets.token_urlsafe(32),
            canonical_params=canonical,
            canonical_hash=c_hash,
            requesting_agent_id=requesting_agent_id,
            required_role=required_role,
            policy_version_id=policy_version_id,
            decision="pending",
            consumed=False,
            expires_at=(now + timedelta(minutes=self._default_expiry)).isoformat(),
            escalation_level=0,
            max_escalation=self._max_escalation,
            created_at=now.isoformat(),
        )
        session.add(approval)
        return approval

    async def decide(
        self,
        session: AsyncSession,
        approval_id: str,
        approver_id: str,
        approver_role: str,
        decision: str,
        reason: str | None = None,
    ) -> Approval:
        result = await session.execute(
            select(Approval).where(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if approval is None:
            raise ApprovalError("Approval not found")

        if approval.decision != "pending":
            raise ApprovalError(f"Approval already resolved: {approval.decision}")

        now = datetime.now(timezone.utc)
        if approval.expires_at and now > datetime.fromisoformat(approval.expires_at):
            approval.decision = "expired"
            raise ApprovalError("Approval has expired")

        if approver_role != approval.required_role:
            raise ApprovalError(
                f"Approver role '{approver_role}' does not match required '{approval.required_role}'"
            )

        if approver_id == approval.requesting_agent_id:
            raise ApprovalError("Agents cannot approve their own actions")

        approval.approver_id = approver_id
        approval.decision = decision
        approval.decision_reason = reason
        approval.resolved_at = now.isoformat()

        return approval

    async def consume(
        self,
        session: AsyncSession,
        approval_id: str,
        expected_params: dict,
        payment_id: str | None = None,
    ) -> Approval:
        result = await session.execute(
            select(Approval).where(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if approval is None:
            raise ApprovalError("Approval not found")

        if approval.consumed:
            raise ApprovalError("Approval already consumed (single-use)")

        if approval.decision != "approved":
            raise ApprovalError(f"Approval not approved: {approval.decision}")

        now = datetime.now(timezone.utc)
        if approval.expires_at and now > datetime.fromisoformat(approval.expires_at):
            approval.decision = "expired"
            raise ApprovalError("Approval expired before consumption")

        expected_hash = canonical_hash(expected_params)
        if expected_hash != approval.canonical_hash:
            raise ApprovalError(
                "Parameter hash mismatch — approved parameters differ from execution parameters"
            )

        approval.consumed = True
        approval.consumed_at = now.isoformat()
        approval.consumed_by_payment = payment_id

        return approval
