from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=False
    )
    supplier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=False
    )
    bank_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("supplier_bank_accounts.id"), nullable=False
    )
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    requested_by_agent: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending_approval"
    )  # pending_approval|approved|executing|completed|failed|cancelled
    approval_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("approvals.id"), nullable=True
    )
    execution_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    executed_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    failed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class TransactionLedger(Base):
    __tablename__ = "transaction_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_ref: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    payment_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("payment_requests.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # initiated|authorized|executed|confirmed|failed|reversed
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    counterparty_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=False
    )
    initiated_by: Mapped[str] = mapped_column(String(36), nullable=False)
    recorded_at: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
