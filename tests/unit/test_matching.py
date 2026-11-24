"""Tests for the 3-way matching engine — integer arithmetic, no floats."""
from __future__ import annotations

import pytest

from backend.simulation.matching import three_way_match


def _po_line(id: str, qty: int, price: int):
    return {"id": id, "quantity": qty, "unit_price_minor": price}


def _gr_line(id: str, po_line_id: str, qty: int):
    return {"id": id, "po_line_id": po_line_id, "quantity_received": qty}


def _inv_line(id: str, po_line_id: str, qty: int, price: int):
    return {"id": id, "po_line_id": po_line_id, "quantity": qty, "unit_price_minor": price}


class TestFullMatch:
    def test_exact_match(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 100, 2500)],
            gr_lines=[_gr_line("gr1", "po1", 100)],
            invoice_lines=[_inv_line("inv1", "po1", 100, 2500)],
        )
        assert result.match_type == "full_match"
        assert result.po_total == 250000
        assert result.invoice_total == 250000
        assert result.line_matches[0].status == "matched"

    def test_multi_line_exact_match(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 10, 5000), _po_line("po2", 20, 3000)],
            gr_lines=[_gr_line("gr1", "po1", 10), _gr_line("gr2", "po2", 20)],
            invoice_lines=[
                _inv_line("inv1", "po1", 10, 5000),
                _inv_line("inv2", "po2", 20, 3000),
            ],
        )
        assert result.match_type == "full_match"
        assert result.po_total == 110000
        assert result.invoice_total == 110000


class TestDiscrepancies:
    def test_quantity_mismatch(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 100, 2500)],
            gr_lines=[_gr_line("gr1", "po1", 80)],
            invoice_lines=[_inv_line("inv1", "po1", 100, 2500)],
        )
        assert result.match_type in ("partial_match", "mismatch")
        discrepancies = result.line_matches[0].discrepancies
        assert any(d["field"] == "quantity" for d in discrepancies)

    def test_price_mismatch(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 100, 2500)],
            gr_lines=[_gr_line("gr1", "po1", 100)],
            invoice_lines=[_inv_line("inv1", "po1", 100, 3500)],
        )
        assert result.match_type == "mismatch"
        discrepancies = result.line_matches[0].discrepancies
        assert any(d["field"] == "unit_price" for d in discrepancies)

    def test_missing_goods_receipt(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 100, 2500)],
            gr_lines=[],
            invoice_lines=[_inv_line("inv1", "po1", 100, 2500)],
        )
        assert result.match_type == "mismatch"
        assert result.line_matches[0].status == "no_receipt"


class TestTolerance:
    def test_within_tolerance(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 100, 2500)],
            gr_lines=[_gr_line("gr1", "po1", 98)],
            invoice_lines=[_inv_line("inv1", "po1", 100, 2500)],
            tolerance_pct=5,
        )
        assert result.tolerance_applied
        assert result.line_matches[0].qty_match

    def test_outside_tolerance(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 100, 2500)],
            gr_lines=[_gr_line("gr1", "po1", 50)],
            invoice_lines=[_inv_line("inv1", "po1", 100, 2500)],
            tolerance_pct=5,
        )
        assert not result.line_matches[0].qty_match


class TestIntegerArithmetic:
    def test_no_floating_point_in_totals(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 3, 3333)],
            gr_lines=[_gr_line("gr1", "po1", 3)],
            invoice_lines=[_inv_line("inv1", "po1", 3, 3333)],
        )
        assert isinstance(result.po_total, int)
        assert isinstance(result.invoice_total, int)
        assert result.po_total == 9999
        assert result.invoice_total == 9999

    def test_large_amounts_no_overflow(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 1000000, 99999)],
            gr_lines=[_gr_line("gr1", "po1", 1000000)],
            invoice_lines=[_inv_line("inv1", "po1", 1000000, 99999)],
        )
        assert result.po_total == 99999000000
        assert result.match_type == "full_match"


class TestFraudDetection:
    def test_inflated_invoice_detected(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 100, 2500)],
            gr_lines=[_gr_line("gr1", "po1", 100)],
            invoice_lines=[_inv_line("inv1", "po1", 100, 25000)],
        )
        assert result.match_type == "mismatch"
        price_disc = [d for d in result.line_matches[0].discrepancies if d["field"] == "unit_price"]
        assert len(price_disc) > 0
        assert price_disc[0]["severity"] == "high"

    def test_duplicate_detection_different_totals(self):
        result = three_way_match(
            po_lines=[_po_line("po1", 100, 2500)],
            gr_lines=[_gr_line("gr1", "po1", 100)],
            invoice_lines=[_inv_line("inv1", "po1", 200, 2500)],
        )
        assert result.invoice_total != result.po_total
