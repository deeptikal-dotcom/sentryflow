from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tool_call_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tool_calls.id"), nullable=False
    )
    nonce: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    canonical_params: Mapped[str] = mapped_column(Text, nullable=False)  # JSON sorted keys
    canonical_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requesting_agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    required_role: Mapped[str] = mapped_column(String(30), nullable=False)
    policy_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policy_versions.id"), nullable=False
    )
    approver_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    decision: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending|approved|denied|expired|consumed
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Cryptographic binding
    approval_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    signing_key_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    signature_algorithm: Mapped[str | None] = mapped_column(String(30), nullable=True)
    transaction_binding: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    verification_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consumed_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    consumed_by_payment: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expires_at: Mapped[str] = mapped_column(String(30), nullable=False)
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_escalation: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    resolved_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
