from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    agent_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # buyer|negotiator|invoice_processor|po_manager|payment_approver
    public_key_ed25519: Mapped[str] = mapped_column(Text, nullable=False)
    public_key_mldsa65: Mapped[str | None] = mapped_column(Text, nullable=True)
    capabilities: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active|suspended|revoked
    registered_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    revoked_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False)


class AgentDelegation(Base):
    __tablename__ = "agent_delegations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    delegator_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    delegate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    scope: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    expires_at: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    revoked_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
