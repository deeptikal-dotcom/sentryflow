from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sequence_num: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(10), nullable=False)  # agent|user|system
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_trace: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    evidence_refs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_ed25519: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_mldsa: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)


class AuditCheckpoint(Base):
    __tablename__ = "audit_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sequence_from: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence_to: Mapped[int] = mapped_column(Integer, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    chain_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_ed25519: Mapped[str] = mapped_column(Text, nullable=False)
    signature_mldsa: Mapped[str | None] = mapped_column(Text, nullable=True)
    exported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exported_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
