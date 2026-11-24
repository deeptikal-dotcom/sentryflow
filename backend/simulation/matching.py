"""Three-way matching engine for SentryFlow.

Matches PO line items <-> Goods Receipt line items <-> Invoice line items.
All amounts are integer minor-currency units (cents).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LineItemMatch:
    po_line_id: str
    gr_line_id: str | None
    invoice_line_id: str | None
    po_qty: int
    po_unit_price: int
    gr_qty: int | None
    invoice_qty: int | None
    invoice_unit_price: int | None
    qty_match: bool = False
    price_match: bool = False
    status: str = "unmatched"
    discrepancies: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MatchResult:
    match_type: str  # full_match|partial_match|mismatch
    line_matches: list[LineItemMatch] = field(default_factory=list)
    discrepancies: list[dict[str, Any]] = field(default_factory=list)
    po_total: int = 0
    gr_total: int = 0
    invoice_total: int = 0
    tolerance_applied: bool = False
    tolerance_pct: int = 0


def three_way_match(
    po_lines: list[dict],
    gr_lines: list[dict],
    invoice_lines: list[dict],
    tolerance_pct: int = 5,
) -> MatchResult:
    result = MatchResult(match_type="full_match", tolerance_pct=tolerance_pct)

    po_total = 0
    gr_total = 0
    inv_total = 0

    gr_by_po_line = {}
    for gr in gr_lines:
        gr_by_po_line[gr["po_line_id"]] = gr

    inv_by_po_line = {}
    for inv in invoice_lines:
        if inv.get("po_line_id"):
            inv_by_po_line[inv["po_line_id"]] = inv

    for po in po_lines:
        po_id = po["id"]
        po_qty = po["quantity"]
        po_price = po["unit_price_minor"]
        po_line_total = po_qty * po_price
        po_total += po_line_total

        gr = gr_by_po_line.get(po_id)
        inv = inv_by_po_line.get(po_id)

        lm = LineItemMatch(
            po_line_id=po_id,
            gr_line_id=gr["id"] if gr else None,
            invoice_line_id=inv["id"] if inv else None,
            po_qty=po_qty,
            po_unit_price=po_price,
            gr_qty=gr["quantity_received"] if gr else None,
            invoice_qty=inv["quantity"] if inv else None,
            invoice_unit_price=inv["unit_price_minor"] if inv else None,
        )

        if gr is None:
            lm.status = "no_receipt"
            lm.discrepancies.append({
                "field": "goods_receipt",
                "expected": "receipt exists",
                "actual": "no receipt",
                "severity": "high",
            })
            result.match_type = "mismatch"
        else:
            gr_qty = gr["quantity_received"]
            gr_total += gr_qty * po_price

            if gr_qty == po_qty:
                lm.qty_match = True
            elif _within_tolerance(po_qty, gr_qty, tolerance_pct):
                lm.qty_match = True
                result.tolerance_applied = True
                lm.discrepancies.append({
                    "field": "quantity",
                    "expected": po_qty,
                    "actual": gr_qty,
                    "severity": "low",
                    "note": f"Within {tolerance_pct}% tolerance",
                })
            else:
                lm.discrepancies.append({
                    "field": "quantity",
                    "expected": po_qty,
                    "actual": gr_qty,
                    "severity": "medium",
                })
                if result.match_type == "full_match":
                    result.match_type = "partial_match"

        if inv is None:
            lm.status = "no_invoice"
            lm.discrepancies.append({
                "field": "invoice_line",
                "expected": "invoice exists",
                "actual": "no invoice",
                "severity": "medium",
            })
            if result.match_type == "full_match":
                result.match_type = "partial_match"
        else:
            inv_qty = inv["quantity"]
            inv_price = inv["unit_price_minor"]
            inv_line_total = inv_qty * inv_price
            inv_total += inv_line_total

            if inv_qty == po_qty:
                lm.qty_match = lm.qty_match  # keep gr verdict
            elif not _within_tolerance(po_qty, inv_qty, tolerance_pct):
                lm.discrepancies.append({
                    "field": "invoice_quantity",
                    "expected": po_qty,
                    "actual": inv_qty,
                    "severity": "medium",
                })

            if inv_price == po_price:
                lm.price_match = True
            elif _within_tolerance(po_price, inv_price, tolerance_pct):
                lm.price_match = True
                result.tolerance_applied = True
            else:
                lm.discrepancies.append({
                    "field": "unit_price",
                    "expected": po_price,
                    "actual": inv_price,
                    "severity": "high",
                })
                result.match_type = "mismatch"

        if lm.status not in ("no_receipt", "no_invoice"):
            if lm.qty_match and lm.price_match and gr is not None and inv is not None:
                lm.status = "matched"
            elif len(lm.discrepancies) > 0:
                lm.status = "discrepancy"
                if result.match_type == "full_match":
                    result.match_type = "partial_match"
            else:
                lm.status = "matched"

        result.line_matches.append(lm)

    result.po_total = po_total
    result.gr_total = gr_total
    result.invoice_total = inv_total

    if po_total != inv_total and inv_total > 0:
        diff_pct = abs(po_total - inv_total) * 100 // max(po_total, 1)
        if diff_pct > tolerance_pct:
            result.discrepancies.append({
                "field": "total_amount",
                "expected": po_total,
                "actual": inv_total,
                "difference_pct": diff_pct,
                "severity": "high",
            })
            result.match_type = "mismatch"

    return result


def _within_tolerance(expected: int, actual: int, pct: int) -> bool:
    if expected == 0:
        return actual == 0
    diff = abs(expected - actual) * 100
    return diff <= expected * pct
