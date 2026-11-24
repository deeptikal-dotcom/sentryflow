"""ERP Simulator — simulated vendor master, PO lifecycle, and 3-way matching.

All amounts are integer minor-currency units (cents).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.goods_receipt import GRLineItem, GoodsReceipt
from backend.models.invoice import Invoice, InvoiceLineItem, ThreeWayMatch
from backend.models.purchase_order import POLineItem, PurchaseOrder
from backend.models.supplier import Supplier
from backend.simulation.matching import three_way_match


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


@dataclass
class MatchReport:
    match_id: str
    match_result: str
    discrepancies: list[dict]
    po_total: int
    invoice_total: int
    tolerance_applied: bool


class ERPSimulator:

    async def validate_invoice(
        self, session: AsyncSession, invoice_id: str
    ) -> MatchReport:
        inv_result = await session.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        invoice = inv_result.scalar_one_or_none()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        if not invoice.po_id:
            raise ValueError(f"Invoice {invoice_id} has no linked PO")

        po_result = await session.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == invoice.po_id)
        )
        po = po_result.scalar_one_or_none()
        if not po:
            raise ValueError(f"PO {invoice.po_id} not found")

        po_lines_result = await session.execute(
            select(POLineItem)
            .where(POLineItem.po_id == po.id)
            .order_by(POLineItem.line_number)
        )
        po_lines = [
            {
                "id": l.id,
                "quantity": l.quantity,
                "unit_price_minor": l.unit_price_minor,
            }
            for l in po_lines_result.scalars().all()
        ]

        gr_result = await session.execute(
            select(GoodsReceipt).where(GoodsReceipt.po_id == po.id)
        )
        receipt = gr_result.scalars().first()

        gr_lines = []
        if receipt:
            gr_lines_result = await session.execute(
                select(GRLineItem).where(GRLineItem.receipt_id == receipt.id)
            )
            gr_lines = [
                {
                    "id": g.id,
                    "po_line_id": g.po_line_id,
                    "quantity_received": g.quantity_received,
                }
                for g in gr_lines_result.scalars().all()
            ]

        inv_lines_result = await session.execute(
            select(InvoiceLineItem)
            .where(InvoiceLineItem.invoice_id == invoice_id)
            .order_by(InvoiceLineItem.line_number)
        )
        inv_lines = [
            {
                "id": il.id,
                "po_line_id": il.po_line_id,
                "quantity": il.quantity,
                "unit_price_minor": il.unit_price_minor,
            }
            for il in inv_lines_result.scalars().all()
        ]

        result = three_way_match(po_lines, gr_lines, inv_lines)

        match_id = _uuid()
        match_record = ThreeWayMatch(
            id=match_id,
            invoice_id=invoice_id,
            po_id=po.id,
            receipt_id=receipt.id if receipt else "none",
            match_result=result.match_type,
            discrepancies=json.dumps(result.discrepancies) if result.discrepancies else None,
            tolerance_applied=result.tolerance_applied,
            tolerance_pct=result.tolerance_pct if result.tolerance_applied else None,
            matched_by="system",
            created_at=_now(),
        )
        session.add(match_record)

        invoice.validation_status = (
            "valid" if result.match_type == "full_match" else "suspicious"
        )
        invoice.validation_details = json.dumps({
            "match_type": result.match_type,
            "discrepancy_count": len(result.discrepancies),
            "po_total": result.po_total,
            "invoice_total": result.invoice_total,
        })

        await session.flush()

        return MatchReport(
            match_id=match_id,
            match_result=result.match_type,
            discrepancies=result.discrepancies,
            po_total=result.po_total,
            invoice_total=result.invoice_total,
            tolerance_applied=result.tolerance_applied,
        )

    async def check_duplicate_invoice(
        self, session: AsyncSession, supplier_id: str, invoice_number: str
    ) -> Invoice | None:
        result = await session.execute(
            select(Invoice).where(
                Invoice.supplier_id == supplier_id,
                Invoice.invoice_number == invoice_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_supplier_risk(
        self, session: AsyncSession, supplier_id: str
    ) -> dict:
        result = await session.execute(
            select(Supplier).where(Supplier.id == supplier_id)
        )
        supplier = result.scalar_one_or_none()
        if not supplier:
            return {"risk_score": 100, "verified": False, "reason": "unknown_supplier"}
        return {
            "risk_score": supplier.risk_score,
            "verified": supplier.verified,
            "name": supplier.name,
        }
