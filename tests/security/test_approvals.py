"""Tests for approval workflows — SI-5, SI-6, SI-7."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import Base
from backend.trust.approval_manager import ApprovalError, ApprovalManager


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("PRAGMA foreign_keys=OFF"))
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(text("PRAGMA foreign_keys=OFF"))
        yield session
    await engine.dispose()


@pytest.fixture
def manager():
    return ApprovalManager(default_expiry_minutes=30, max_escalation=2)


PAYMENT_PARAMS = {
    "supplier_id": "supplier-001",
    "amount_minor": 500000,
    "currency": "USD",
    "bank_account_id": "bank-001",
}


class TestSI5_ApprovalBindsParameters:
    @pytest.mark.asyncio
    async def test_consume_with_matching_params(self, db, manager):
        approval = await manager.create_approval_request(
            db, "tc-001", PAYMENT_PARAMS, "agent-001", "finance_approver", "policy-v1"
        )
        await db.flush()

        await manager.decide(db, approval.id, "user-cfo", "finance_approver", "approved")
        await db.flush()

        result = await manager.consume(db, approval.id, PAYMENT_PARAMS)
        assert result.consumed is True

    @pytest.mark.asyncio
    async def test_consume_with_different_amount_rejected(self, db, manager):
        approval = await manager.create_approval_request(
            db, "tc-002", PAYMENT_PARAMS, "agent-001", "finance_approver", "policy-v1"
        )
        await db.flush()
        await manager.decide(db, approval.id, "user-cfo", "finance_approver", "approved")
        await db.flush()

        tampered = {**PAYMENT_PARAMS, "amount_minor": 5000000}
        with pytest.raises(ApprovalError, match="Parameter hash mismatch"):
            await manager.consume(db, approval.id, tampered)

    @pytest.mark.asyncio
    async def test_consume_with_different_supplier_rejected(self, db, manager):
        approval = await manager.create_approval_request(
            db, "tc-003", PAYMENT_PARAMS, "agent-001", "finance_approver", "policy-v1"
        )
        await db.flush()
        await manager.decide(db, approval.id, "user-cfo", "finance_approver", "approved")
        await db.flush()

        tampered = {**PAYMENT_PARAMS, "supplier_id": "supplier-evil"}
        with pytest.raises(ApprovalError, match="Parameter hash mismatch"):
            await manager.consume(db, approval.id, tampered)

    @pytest.mark.asyncio
    async def test_consume_with_different_bank_rejected(self, db, manager):
        approval = await manager.create_approval_request(
            db, "tc-004", PAYMENT_PARAMS, "agent-001", "finance_approver", "policy-v1"
        )
        await db.flush()
        await manager.decide(db, approval.id, "user-cfo", "finance_approver", "approved")
        await db.flush()

        tampered = {**PAYMENT_PARAMS, "bank_account_id": "bank-evil"}
        with pytest.raises(ApprovalError, match="Parameter hash mismatch"):
            await manager.consume(db, approval.id, tampered)


class TestSI6_ReplayProtection:
    @pytest.mark.asyncio
    async def test_double_consume_rejected(self, db, manager):
        approval = await manager.create_approval_request(
            db, "tc-010", PAYMENT_PARAMS, "agent-001", "finance_approver", "policy-v1"
        )
        await db.flush()
        await manager.decide(db, approval.id, "user-cfo", "finance_approver", "approved")
        await db.flush()

        await manager.consume(db, approval.id, PAYMENT_PARAMS)
        await db.flush()

        with pytest.raises(ApprovalError, match="already consumed"):
            await manager.consume(db, approval.id, PAYMENT_PARAMS)

    @pytest.mark.asyncio
    async def test_unique_nonce_per_approval(self, db, manager):
        a1 = await manager.create_approval_request(
            db, "tc-011", PAYMENT_PARAMS, "agent-001", "finance_approver", "policy-v1"
        )
        a2 = await manager.create_approval_request(
            db, "tc-012", PAYMENT_PARAMS, "agent-001", "finance_approver", "policy-v1"
        )
        assert a1.nonce != a2.nonce


class TestSI7_AgentCannotSelfApprove:
    @pytest.mark.asyncio
    async def test_agent_cannot_approve_own_action(self, db, manager):
        approval = await manager.create_approval_request(
            db, "tc-020", PAYMENT_PARAMS, "agent-001", "finance_approver", "policy-v1"
        )
        await db.flush()

        with pytest.raises(ApprovalError, match="cannot approve their own"):
            await manager.decide(db, approval.id, "agent-001", "finance_approver", "approved")

    @pytest.mark.asyncio
    async def test_wrong_role_rejected(self, db, manager):
        approval = await manager.create_approval_request(
            db, "tc-021", PAYMENT_PARAMS, "agent-001", "finance_approver", "policy-v1"
        )
        await db.flush()

        with pytest.raises(ApprovalError, match="does not match"):
            await manager.decide(db, approval.id, "user-analyst", "security_analyst", "approved")

    @pytest.mark.asyncio
    async def test_already_decided_rejected(self, db, manager):
        approval = await manager.create_approval_request(
            db, "tc-022", PAYMENT_PARAMS, "agent-001", "finance_approver", "policy-v1"
        )
        await db.flush()
        await manager.decide(db, approval.id, "user-cfo", "finance_approver", "denied", "Suspicious")
        await db.flush()

        with pytest.raises(ApprovalError, match="already resolved"):
            await manager.decide(db, approval.id, "user-other", "finance_approver", "approved")
