from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    incident_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # prompt_injection|supplier_fraud|invoice_fraud|unauthorized_action|anomaly|policy_violation
    severity: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # low|medium|high|critical
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=True
    )
    source_document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=True
    )
    source_tool_call_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tool_calls.id"), nullable=True
    )
    evidence_refs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="detected"
    )  # detected|investigating|mitigated|resolved|false_positive
    assigned_to: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[str] = mapped_column(String(30), nullable=False)
    resolved_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
