"""Append-only, hash-chained audit logger for SentryFlow.

Implements SI-8: decisions and evidence are auditable with tamper detection.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit import AuditCheckpoint, AuditLog
from backend.trust.crypto import canonical_json


GENESIS_HASH = "0" * 64


class AuditLogger:
    def __init__(self):
        self._checkpoint_interval = 100

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

        now = datetime.now(timezone.utc).isoformat()

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
