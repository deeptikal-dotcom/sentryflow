from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # AES-256-GCM
    classification: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # read_only|write|financial|critical
    injection_context: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    policy_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("policy_versions.id"), nullable=True
    )
    policy_result: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # allow|deny|escalate
    policy_rule_trace: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100
    risk_factors: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    execution_result: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending|authorized|denied|escalated|approved|executing|completed|failed
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    executed_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
