from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    verification_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)  # 0-100
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False)


class SupplierBankAccount(Base):
    __tablename__ = "supplier_bank_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=False
    )
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number_hmac: Mapped[str] = mapped_column(Text, nullable=False)  # HMAC-SHA256 fingerprint
    routing_number_hmac: Mapped[str] = mapped_column(Text, nullable=False)  # HMAC-SHA256 fingerprint
    account_number_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # AES-256-GCM
    routing_number_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # AES-256-GCM
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    changed_by: Mapped[str] = mapped_column(String(36), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    superseded_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
