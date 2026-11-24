from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    contract_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=False
    )
    effective_date: Mapped[str] = mapped_column(String(10), nullable=False)
    expiry_date: Mapped[str] = mapped_column(String(10), nullable=False)
    terms: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    total_value_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft|active|expired|terminated
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False)
