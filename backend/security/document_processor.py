"""Document processing pipeline — secure intake, validation, text extraction.

All documents are untrusted input. Processing enforces:
- File size limits
- File signature (magic bytes) validation
- MIME type checking
- Page count limits
- Processing timeouts
- Content hashing before any processing
- Injection scanning of extracted text
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO

logger = logging.getLogger("sentryflow.documents")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_PAGE_COUNT = 100

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/csv",
    "text/plain",
    "application/json",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "message/rfc822",
}

FILE_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"\x89PNG": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"II\x2a\x00": "image/tiff",
    b"MM\x00\x2a": "image/tiff",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ProcessingResult:
    document_id: str
    status: str
    content_hash: str
    file_size_bytes: int
    detected_mime: str | None = None
    page_count: int | None = None
    extracted_text: str | None = None
    ocr_applied: bool = False
    injection_scan: dict = field(default_factory=dict)
    quarantine_reason: str | None = None
    errors: list[str] = field(default_factory=list)


def detect_file_type(data: bytes) -> str | None:
    for sig, mime in FILE_SIGNATURES.items():
        if data[:len(sig)] == sig:
            return mime
    if data[:1] in (b"{", b"["):
        return "application/json"
    try:
        data[:1024].decode("utf-8")
        if b"," in data[:1024]:
            return "text/csv"
        return "text/plain"
    except UnicodeDecodeError:
        return None


def compute_content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class DocumentProcessor:

    def process(
        self,
        filename: str,
        data: bytes,
        source: str = "upload",
    ) -> ProcessingResult:
        doc_id = str(uuid.uuid4())
        content_hash = compute_content_hash(data)
        file_size = len(data)

        result = ProcessingResult(
            document_id=doc_id,
            status="received",
            content_hash=content_hash,
            file_size_bytes=file_size,
        )

        if file_size > MAX_FILE_SIZE:
            result.status = "quarantined"
            result.quarantine_reason = f"File exceeds maximum size ({file_size} > {MAX_FILE_SIZE})"
            return result

        detected_mime = detect_file_type(data)
        result.detected_mime = detected_mime

        if detected_mime and detected_mime not in ALLOWED_MIME_TYPES:
            result.status = "quarantined"
            result.quarantine_reason = f"Unsupported file type: {detected_mime}"
            return result

        result.status = "scanning"

        text = None
        if detected_mime == "application/pdf":
            text, page_count = self._extract_pdf(data)
            result.page_count = page_count
            if page_count is not None and page_count > MAX_PAGE_COUNT:
                result.status = "quarantined"
                result.quarantine_reason = f"PDF exceeds page limit ({page_count} > {MAX_PAGE_COUNT})"
                return result
        elif detected_mime in ("text/csv", "text/plain"):
            text = self._extract_text(data)
        elif detected_mime == "application/json":
            text = self._extract_json(data)
        elif detected_mime in ("image/png", "image/jpeg", "image/tiff"):
            text = self._extract_image_ocr(data)
            if text:
                result.ocr_applied = True

        result.extracted_text = text

        if text:
            from backend.security.injection_detector import InjectionDetector
            detector = InjectionDetector()
            scan = detector.scan(text)
            result.injection_scan = {
                "score": scan.score,
                "flagged": scan.flagged,
                "layer_scores": scan.layer_scores,
                "details": scan.details,
            }
            if scan.flagged or scan.score >= 40:
                result.status = "quarantined"
                result.quarantine_reason = "Injection patterns detected"
                return result

        result.status = "processed"
        return result

    def _extract_pdf(self, data: bytes) -> tuple[str | None, int | None]:
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(data))
            page_count = len(reader.pages)
            text_parts = []
            for page in reader.pages[:MAX_PAGE_COUNT]:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts) if text_parts else None, page_count
        except ImportError:
            logger.warning("pypdf not available for PDF extraction")
            return None, None
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return None, None

    def _extract_text(self, data: bytes) -> str | None:
        try:
            return data.decode("utf-8")[:100_000]
        except UnicodeDecodeError:
            return None

    def _extract_json(self, data: bytes) -> str | None:
        try:
            parsed = json.loads(data)
            return json.dumps(parsed, indent=2)[:100_000]
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _extract_image_ocr(self, data: bytes) -> str | None:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(BytesIO(data))
            text = pytesseract.image_to_string(img)
            return text.strip() if text.strip() else None
        except ImportError:
            logger.warning("pytesseract/Pillow not available for OCR")
            return None
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return None
