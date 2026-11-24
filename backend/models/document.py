from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doc_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # invoice_pdf|email|contract|po|csv|json|image
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_signature: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    injection_scan_result: Mapped[str] = mapped_column(
        Text, nullable=False, default='{"score":0,"flagged":false}'
    )  # JSON
    provenance: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="received"
    )  # received|scanning|scanned|processing|processed|quarantined
    quarantine_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
