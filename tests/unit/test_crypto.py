"""Tests for the cryptographic module."""
from __future__ import annotations

import os

import pytest

from backend.trust.crypto import (
    canonical_hash,
    canonical_json,
    decrypt_field,
    detect_pqc_capabilities,
    encrypt_field,
    generate_ed25519_keypair,
    hmac_fingerprint,
    hybrid_sign,
    hybrid_verify,
    sign_ed25519,
    verify_ed25519,
)


class TestEd25519:
    def test_keypair_generation(self):
        priv, pub = generate_ed25519_keypair()
        assert len(priv) == 32
        assert len(pub) == 32

    def test_sign_and_verify(self):
        priv, pub = generate_ed25519_keypair()
        data = b"test message"
        sig = sign_ed25519(priv, data)
        assert verify_ed25519(pub, sig, data)

    def test_verify_fails_on_wrong_data(self):
        priv, pub = generate_ed25519_keypair()
        sig = sign_ed25519(priv, b"original")
        assert not verify_ed25519(pub, sig, b"tampered")

    def test_verify_fails_on_wrong_key(self):
        priv1, _ = generate_ed25519_keypair()
        _, pub2 = generate_ed25519_keypair()
        sig = sign_ed25519(priv1, b"data")
        assert not verify_ed25519(pub2, sig, b"data")


class TestAESGCM:
    def test_encrypt_decrypt_roundtrip(self):
        key = os.urandom(32)
        plaintext = "sensitive bank account: 1234567890"
        encrypted = encrypt_field(key, plaintext)
        decrypted = decrypt_field(key, encrypted)
        assert decrypted == plaintext

    def test_different_nonce_per_encryption(self):
        key = os.urandom(32)
        enc1 = encrypt_field(key, "same data")
        enc2 = encrypt_field(key, "same data")
        assert enc1 != enc2  # unique nonce per operation

    def test_wrong_key_fails(self):
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        encrypted = encrypt_field(key1, "secret")
        with pytest.raises(Exception):
            decrypt_field(key2, encrypted)

    def test_invalid_key_length_rejected(self):
        with pytest.raises(ValueError, match="32 bytes"):
            encrypt_field(os.urandom(16), "data")


class TestHMACFingerprint:
    def test_deterministic(self):
        key = b"fingerprint-key"
        fp1 = hmac_fingerprint(key, "12345678")
        fp2 = hmac_fingerprint(key, "12345678")
        assert fp1 == fp2

    def test_different_values_different_fingerprints(self):
        key = b"fingerprint-key"
        fp1 = hmac_fingerprint(key, "12345678")
        fp2 = hmac_fingerprint(key, "87654321")
        assert fp1 != fp2

    def test_different_keys_different_fingerprints(self):
        fp1 = hmac_fingerprint(b"key-a", "12345678")
        fp2 = hmac_fingerprint(b"key-b", "12345678")
        assert fp1 != fp2

    def test_fingerprint_is_hex_sha256(self):
        fp = hmac_fingerprint(b"key", "value")
        assert len(fp) == 64


class TestCanonicalSerialization:
    def test_sorted_keys(self):
        data = {"z": 1, "a": 2, "m": 3}
        result = canonical_json(data)
        assert result == b'{"a":2,"m":3,"z":1}'

    def test_no_whitespace(self):
        data = {"key": "value", "nested": {"a": 1}}
        result = canonical_json(data)
        assert b" " not in result
        assert b"\n" not in result

    def test_hash_deterministic(self):
        data = {"amount": 12550, "supplier_id": "abc-123"}
        h1 = canonical_hash(data)
        h2 = canonical_hash(data)
        assert h1 == h2

    def test_hash_changes_on_modification(self):
        h1 = canonical_hash({"amount": 12550})
        h2 = canonical_hash({"amount": 12551})
        assert h1 != h2


class TestHybridSignature:
    def test_ed25519_only_sign_verify(self):
        priv, pub = generate_ed25519_keypair()
        data = b"transaction data"
        sig = hybrid_sign(priv, data, pqc_mode="optional")
        assert sig.ed25519_sig is not None
        assert sig.mldsa_sig is None
        assert hybrid_verify(pub, data, sig, pqc_mode="optional")

    def test_ed25519_only_tamper_detected(self):
        priv, pub = generate_ed25519_keypair()
        sig = hybrid_sign(priv, b"original", pqc_mode="optional")
        assert not hybrid_verify(pub, b"tampered", sig, pqc_mode="optional")

    def test_pqc_required_without_key_raises(self):
        priv, _ = generate_ed25519_keypair()
        with pytest.raises(RuntimeError, match="ML-DSA-65"):
            hybrid_sign(priv, b"data", pqc_mode="required")


class TestPQCDetection:
    def test_detect_returns_capabilities(self):
        caps = detect_pqc_capabilities()
        assert isinstance(caps.mldsa_available, bool)
        assert isinstance(caps.mlkem_available, bool)
