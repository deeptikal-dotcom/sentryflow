from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("supplier_id", "invoice_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    supplier_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=True
    )
    po_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("purchase_orders.id"), nullable=True
    )
    total_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    bank_account_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("supplier_bank_accounts.id"), nullable=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=True
    )
    validation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending|valid|suspicious|rejected
    validation_details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    duplicate_of: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="received"
    )  # received|processing|validated|approved|paid|rejected|disputed
    processed_by_agent: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=True
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False)


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"
    __table_args__ = (UniqueConstraint("invoice_id", "line_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    po_line_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("po_line_items.id"), nullable=True
    )
    gr_line_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("gr_line_items.id"), nullable=True
    )
    match_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unmatched"
    )  # unmatched|matched|discrepancy


class ThreeWayMatch(Base):
    __tablename__ = "three_way_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=False
    )
    po_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("purchase_orders.id"), nullable=False
    )
    receipt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("goods_receipts.id"), nullable=False
    )
    match_result: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # full_match|partial_match|mismatch
    discrepancies: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    tolerance_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tolerance_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_by: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
