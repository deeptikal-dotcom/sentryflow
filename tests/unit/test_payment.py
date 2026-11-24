"""Tests for payment simulator — idempotency, duplicate detection, integer amounts."""
from __future__ import annotations

import pytest
from backend.simulation.payment_simulator import compute_idempotency_key


class TestIdempotencyKey:
    def test_deterministic(self):
        k1 = compute_idempotency_key("inv-1", "sup-1", 50000, "USD")
        k2 = compute_idempotency_key("inv-1", "sup-1", 50000, "USD")
        assert k1 == k2

    def test_different_amount_different_key(self):
        k1 = compute_idempotency_key("inv-1", "sup-1", 50000, "USD")
        k2 = compute_idempotency_key("inv-1", "sup-1", 50001, "USD")
        assert k1 != k2

    def test_different_supplier_different_key(self):
        k1 = compute_idempotency_key("inv-1", "sup-1", 50000, "USD")
        k2 = compute_idempotency_key("inv-1", "sup-2", 50000, "USD")
        assert k1 != k2

    def test_different_invoice_different_key(self):
        k1 = compute_idempotency_key("inv-1", "sup-1", 50000, "USD")
        k2 = compute_idempotency_key("inv-2", "sup-1", 50000, "USD")
        assert k1 != k2

    def test_different_currency_different_key(self):
        k1 = compute_idempotency_key("inv-1", "sup-1", 50000, "USD")
        k2 = compute_idempotency_key("inv-1", "sup-1", 50000, "EUR")
        assert k1 != k2

    def test_key_is_sha256_hex(self):
        k = compute_idempotency_key("inv-1", "sup-1", 50000, "USD")
        assert len(k) == 64
        int(k, 16)  # validates hex

    def test_integer_amounts_only(self):
        k = compute_idempotency_key("inv-1", "sup-1", 12550, "USD")
        assert isinstance(k, str)
