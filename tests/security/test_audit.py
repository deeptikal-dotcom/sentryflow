"""Tests for the tamper-evident audit trail — SI-8."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.audit.audit_logger import AuditLogger, GENESIS_HASH
from backend.database import Base


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def logger():
    return AuditLogger()


class TestAuditChain:
    @pytest.mark.asyncio
    async def test_first_record_links_to_genesis(self, db, logger):
        entry = await logger.log(
            db, "test_event", "system", "sys-001", "test_action"
        )
        assert entry.prev_hash == GENESIS_HASH
        assert entry.sequence_num == 1

    @pytest.mark.asyncio
    async def test_chain_links_records(self, db, logger):
        e1 = await logger.log(db, "event_1", "system", "sys-001", "action_1")
        await db.flush()
        e2 = await logger.log(db, "event_2", "user", "user-001", "action_2")
        await db.flush()

        assert e2.prev_hash == e1.record_hash
        assert e2.sequence_num == 2

    @pytest.mark.asyncio
    async def test_chain_verification_passes(self, db, logger):
        for i in range(10):
            await logger.log(
                db, f"event_{i}", "system", "sys-001", f"action_{i}",
                risk_score=i * 10,
            )
            await db.flush()

        valid, errors = await logger.verify_chain(db)
        assert valid
        assert errors == []

    @pytest.mark.asyncio
    async def test_tampered_record_detected(self, db, logger):
        for i in range(5):
            await logger.log(db, f"event_{i}", "system", "sys-001", f"action_{i}")
            await db.flush()

        from sqlalchemy import select, update
        from backend.models.audit import AuditLog

        result = await db.execute(
            select(AuditLog).where(AuditLog.sequence_num == 3)
        )
        record = result.scalar_one()
        record.decision_summary = "TAMPERED DATA"
        await db.flush()

        valid, errors = await logger.verify_chain(db)
        assert not valid
        assert any("hash mismatch" in e for e in errors)


class TestAuditCheckpoints:
    @pytest.mark.asyncio
    async def test_create_checkpoint(self, db, logger):
        from backend.trust.crypto import generate_ed25519_keypair
        for i in range(5):
            await logger.log(db, f"event_{i}", "system", "sys", f"action_{i}")
            await db.flush()

        priv, pub = generate_ed25519_keypair()
        cp = await logger.create_checkpoint(db, signing_key=priv)
        assert cp is not None
        assert cp.sequence_from == 1
        assert cp.sequence_to == 5
        assert cp.record_count == 5
        assert cp.signature_ed25519 is not None
        assert len(cp.checkpoint_hash) == 64

    @pytest.mark.asyncio
    async def test_no_checkpoint_when_empty(self, db, logger):
        from backend.trust.crypto import generate_ed25519_keypair
        priv, _ = generate_ed25519_keypair()
        cp = await logger.create_checkpoint(db, signing_key=priv)
        assert cp is None

    @pytest.mark.asyncio
    async def test_checkpoint_pqc_signed(self, db, logger):
        from backend.trust.crypto import generate_ed25519_keypair, generate_mldsa65_keypair
        for i in range(3):
            await logger.log(db, f"event_{i}", "system", "sys", f"action_{i}")
            await db.flush()

        ed_priv, _ = generate_ed25519_keypair()
        mldsa_priv, _ = generate_mldsa65_keypair()
        cp = await logger.create_checkpoint(db, signing_key=ed_priv, mldsa_key=mldsa_priv)
        assert cp is not None
        assert cp.signature_mldsa is not None

    @pytest.mark.asyncio
    async def test_checkpoint_only_new_records(self, db, logger):
        from backend.trust.crypto import generate_ed25519_keypair
        priv, _ = generate_ed25519_keypair()

        for i in range(3):
            await logger.log(db, f"event_{i}", "system", "sys", f"action_{i}")
            await db.flush()
        cp1 = await logger.create_checkpoint(db, signing_key=priv)
        await db.flush()
        assert cp1.record_count == 3

        for i in range(3, 7):
            await logger.log(db, f"event_{i}", "system", "sys", f"action_{i}")
            await db.flush()
        cp2 = await logger.create_checkpoint(db, signing_key=priv)
        assert cp2.sequence_from == 4
        assert cp2.sequence_to == 7
        assert cp2.record_count == 4

    @pytest.mark.asyncio
    async def test_export_checkpoint(self, db, logger):
        from backend.trust.crypto import generate_ed25519_keypair
        priv, _ = generate_ed25519_keypair()

        for i in range(5):
            await logger.log(db, f"event_{i}", "system", "sys", f"action_{i}")
            await db.flush()
        cp = await logger.create_checkpoint(db, signing_key=priv)
        await db.flush()

        export = await logger.export_checkpoint(db, cp.id)
        assert export["checkpoint"]["id"] == cp.id
        assert len(export["records"]) == 5


class TestAuditContent:
    @pytest.mark.asyncio
    async def test_structured_decision_logged(self, db, logger):
        entry = await logger.log(
            db,
            event_type="action_decided",
            actor_type="agent",
            actor_id="agent-001",
            action="create_payment",
            target_type="payment",
            target_id="pay-001",
            decision_summary="Policy denied: amount exceeds threshold",
            rule_trace=[{"rule_id": "high_amount", "matched": True}],
            risk_score=85,
        )
        assert entry.decision_summary == "Policy denied: amount exceeds threshold"
        assert entry.risk_score == 85
        assert '"rule_id"' in entry.rule_trace

    @pytest.mark.asyncio
    async def test_monotonic_sequence(self, db, logger):
        entries = []
        for i in range(5):
            e = await logger.log(db, f"event_{i}", "system", "sys", f"act_{i}")
            await db.flush()
            entries.append(e)

        for i in range(1, len(entries)):
            assert entries[i].sequence_num == entries[i - 1].sequence_num + 1
