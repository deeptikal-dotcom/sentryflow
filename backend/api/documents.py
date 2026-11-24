"""Document upload and processing API."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.audit.audit_logger import AuditLogger
from backend.database import get_session
from backend.models.document import Document
from backend.models.user import User
from backend.security.document_processor import DocumentProcessor

router = APIRouter()
audit = AuditLogger()
processor = DocumentProcessor()


@router.post("/upload")
async def upload_document(
    file: UploadFile,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    data = await file.read()
    result = processor.process(file.filename or "unknown", data)

    doc = Document(
        id=result.document_id,
        doc_type=_classify_doc_type(result.detected_mime),
        original_filename=file.filename,
        content_hash=result.content_hash,
        file_signature=result.detected_mime,
        file_size_bytes=result.file_size_bytes,
        page_count=result.page_count,
        mime_type=result.detected_mime,
        extracted_text=result.extracted_text,
        ocr_applied=result.ocr_applied,
        injection_scan_result=json.dumps(result.injection_scan),
        provenance=json.dumps({
            "source": "upload",
            "uploaded_by": user.id,
            "original_filename": file.filename,
        }),
        status=result.status,
        quarantine_reason=result.quarantine_reason,
        created_at=datetime.now(UTC).isoformat(),
    )
    session.add(doc)

    await audit.log(
        session, "document_uploaded", "user", user.id,
        f"upload:{file.filename}",
        target_type="document", target_id=result.document_id,
        risk_score=result.injection_scan.get("score", 0) if result.injection_scan else 0,
    )
    await session.commit()

    return {
        "document_id": result.document_id,
        "status": result.status,
        "content_hash": result.content_hash,
        "injection_scan": result.injection_scan,
        "quarantine_reason": result.quarantine_reason,
    }


@router.get("/")
async def list_documents(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(
        select(Document).order_by(Document.created_at.desc()).limit(50)
    )
    docs = result.scalars().all()
    return {
        "documents": [
            {
                "id": d.id,
                "doc_type": d.doc_type,
                "original_filename": d.original_filename,
                "status": d.status,
                "content_hash": d.content_hash[:12] + "...",
                "file_size_bytes": d.file_size_bytes,
                "created_at": d.created_at,
            }
            for d in docs
        ]
    }


def _classify_doc_type(mime: str | None) -> str:
    if mime == "application/pdf":
        return "invoice_pdf"
    if mime in ("text/csv",):
        return "csv"
    if mime == "application/json":
        return "json"
    if mime and mime.startswith("image/"):
        return "image"
    return "text"
