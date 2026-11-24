from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    po_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("purchase_orders.id"), nullable=False
    )
    supplier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=False
    )
    received_by: Mapped[str] = mapped_column(String(36), nullable=False)
    received_date: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending|confirmed|disputed
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)


class GRLineItem(Base):
    __tablename__ = "gr_line_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    receipt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("goods_receipts.id"), nullable=False
    )
    po_line_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("po_line_items.id"), nullable=False
    )
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False)
    condition: Mapped[str] = mapped_column(
        String(20), nullable=False, default="acceptable"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
