"""Append-only, hash-chained audit logger for SentryFlow.

Implements SI-8: decisions and evidence are auditable with tamper detection.
"""
from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit import AuditCheckpoint, AuditLog
from backend.trust.crypto import canonical_json

GENESIS_HASH = "0" * 64


class AuditLogger:
    def __init__(self, checkpoint_interval: int = 100):
        self._checkpoint_interval = checkpoint_interval

    async def log(
        self,
        session: AsyncSession,
        event_type: str,
        actor_type: str,
        actor_id: str,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        decision_summary: str | None = None,
        rule_trace: list[dict] | None = None,
        evidence_refs: list[str] | None = None,
        risk_score: int | None = None,
    ) -> AuditLog:
        result = await session.execute(
            select(func.max(AuditLog.sequence_num))
        )
        last_seq = result.scalar() or 0
        new_seq = last_seq + 1

        prev_result = await session.execute(
            select(AuditLog.record_hash)
            .where(AuditLog.sequence_num == last_seq)
        )
        prev_hash = prev_result.scalar() or GENESIS_HASH

        now = datetime.now(UTC).isoformat()

        record_data = canonical_json({
            "sequence_num": new_seq,
            "event_type": event_type,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "decision_summary": decision_summary,
            "risk_score": risk_score,
            "prev_hash": prev_hash,
            "created_at": now,
        })
        record_hash = hashlib.sha256(record_data).hexdigest()

        entry = AuditLog(
            sequence_num=new_seq,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            decision_summary=decision_summary,
            rule_trace=json.dumps(rule_trace) if rule_trace else None,
            evidence_refs=json.dumps(evidence_refs) if evidence_refs else None,
            risk_score=risk_score,
            prev_hash=prev_hash,
            record_hash=record_hash,
            created_at=now,
        )
        session.add(entry)
        return entry

    async def create_checkpoint(
        self,
        session: AsyncSession,
        signing_key: bytes,
        mldsa_key: bytes | None = None,
    ) -> AuditCheckpoint | None:
        from backend.trust.crypto import sign_ed25519

        last_cp_result = await session.execute(
            select(func.max(AuditCheckpoint.sequence_to))
        )
        last_cp_seq = last_cp_result.scalar() or 0

        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.sequence_num > last_cp_seq)
            .order_by(AuditLog.sequence_num)
        )
        records = result.scalars().all()
        if not records:
            return None

        seq_from = records[0].sequence_num
        seq_to = records[-1].sequence_num
        chain_hash = records[-1].record_hash

        cp_data = canonical_json({
            "sequence_from": seq_from,
            "sequence_to": seq_to,
            "record_count": len(records),
            "chain_hash": chain_hash,
        })
        checkpoint_hash = hashlib.sha256(cp_data).hexdigest()

        ed_sig = sign_ed25519(signing_key, cp_data)
        ed_sig_b64 = base64.b64encode(ed_sig).decode("ascii")

        mldsa_sig_b64 = None
        if mldsa_key:
            try:
                from backend.trust.crypto import sign_mldsa65
                mldsa_sig = sign_mldsa65(mldsa_key, cp_data)
                mldsa_sig_b64 = base64.b64encode(mldsa_sig).decode("ascii")
            except Exception:
                pass

        now = datetime.now(UTC).isoformat()
        cp = AuditCheckpoint(
            id=str(uuid.uuid4()),
            sequence_from=seq_from,
            sequence_to=seq_to,
            record_count=len(records),
            chain_hash=chain_hash,
            checkpoint_hash=checkpoint_hash,
            signature_ed25519=ed_sig_b64,
            signature_mldsa=mldsa_sig_b64,
            created_at=now,
        )
        session.add(cp)
        return cp

    async def export_checkpoint(
        self, session: AsyncSession, checkpoint_id: str,
    ) -> dict:
        cp_result = await session.execute(
            select(AuditCheckpoint).where(AuditCheckpoint.id == checkpoint_id)
        )
        cp = cp_result.scalar_one_or_none()
        if cp is None:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        records_result = await session.execute(
            select(AuditLog)
            .where(AuditLog.sequence_num >= cp.sequence_from)
            .where(AuditLog.sequence_num <= cp.sequence_to)
            .order_by(AuditLog.sequence_num)
        )
        records = records_result.scalars().all()

        return {
            "checkpoint": {
                "id": cp.id,
                "sequence_from": cp.sequence_from,
                "sequence_to": cp.sequence_to,
                "record_count": cp.record_count,
                "chain_hash": cp.chain_hash,
                "checkpoint_hash": cp.checkpoint_hash,
                "signature_ed25519": cp.signature_ed25519,
                "signature_mldsa": cp.signature_mldsa,
                "created_at": cp.created_at,
            },
            "records": [
                {
                    "sequence_num": r.sequence_num,
                    "event_type": r.event_type,
                    "actor_type": r.actor_type,
                    "actor_id": r.actor_id,
                    "action": r.action,
                    "target_type": r.target_type,
                    "target_id": r.target_id,
                    "decision_summary": r.decision_summary,
                    "risk_score": r.risk_score,
                    "prev_hash": r.prev_hash,
                    "record_hash": r.record_hash,
                    "created_at": r.created_at,
                }
                for r in records
            ],
        }

    async def verify_chain(self, session: AsyncSession) -> tuple[bool, list[str]]:
        result = await session.execute(
            select(AuditLog).order_by(AuditLog.sequence_num)
        )
        records = result.scalars().all()

        errors = []
        expected_prev = GENESIS_HASH
        expected_seq = 1

        for record in records:
            if record.sequence_num != expected_seq:
                errors.append(
                    f"Sequence gap: expected {expected_seq}, got {record.sequence_num}"
                )

            if record.prev_hash != expected_prev:
                errors.append(
                    f"Chain break at seq {record.sequence_num}: "
                    f"prev_hash mismatch"
                )

            record_data = canonical_json({
                "sequence_num": record.sequence_num,
                "event_type": record.event_type,
                "actor_type": record.actor_type,
                "actor_id": record.actor_id,
                "action": record.action,
                "target_type": record.target_type,
                "target_id": record.target_id,
                "decision_summary": record.decision_summary,
                "risk_score": record.risk_score,
                "prev_hash": record.prev_hash,
                "created_at": record.created_at,
            })
            expected_hash = hashlib.sha256(record_data).hexdigest()

            if record.record_hash != expected_hash:
                errors.append(
                    f"Record hash mismatch at seq {record.sequence_num}"
                )

            expected_prev = record.record_hash
            expected_seq = record.sequence_num + 1

        return len(errors) == 0, errors
