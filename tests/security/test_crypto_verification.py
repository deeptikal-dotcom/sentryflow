"""Comprehensive cryptographic verification — exercises all crypto operations
in the actual runtime environment and verifies correct behavior."""
from __future__ import annotations

import json
import os

import pytest

from backend.trust.crypto import (
    generate_ed25519_keypair,
    sign_ed25519,
    verify_ed25519,
    encrypt_field,
    decrypt_field,
    hmac_fingerprint,
    canonical_json,
    canonical_hash,
    detect_pqc_capabilities,
)

_pqc = detect_pqc_capabilities()
PQC_AVAILABLE = _pqc.mldsa_available and _pqc.mlkem_available


class TestEd25519Signatures:
    def test_sign_and_verify(self):
        priv, pub = generate_ed25519_keypair()
        data = b"test message"
        sig = sign_ed25519(priv, data)
        assert verify_ed25519(pub, sig, data)

    def test_invalid_signature_rejected(self):
        priv, pub = generate_ed25519_keypair()
        data = b"test message"
        sig = sign_ed25519(priv, data)
        tampered_sig = bytearray(sig)
        tampered_sig[0] ^= 0xFF
        assert not verify_ed25519(pub, bytes(tampered_sig), data)

    def test_wrong_key_rejected(self):
        priv1, pub1 = generate_ed25519_keypair()
        _, pub2 = generate_ed25519_keypair()
        sig = sign_ed25519(priv1, b"data")
        assert not verify_ed25519(pub2, sig, b"data")

    def test_tampered_data_rejected(self):
        priv, pub = generate_ed25519_keypair()
        sig = sign_ed25519(priv, b"original data")
        assert not verify_ed25519(pub, sig, b"tampered data")


class TestAESGCMEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        key = os.urandom(32)
        plaintext = "sensitive bank account: 1234567890"
        encrypted = encrypt_field(key, plaintext)
        decrypted = decrypt_field(key, encrypted)
        assert decrypted == plaintext

    def test_different_nonces_per_encryption(self):
        key = os.urandom(32)
        enc1 = encrypt_field(key, "same data")
        enc2 = encrypt_field(key, "same data")
        assert enc1 != enc2  # unique nonce each time

    def test_wrong_key_fails(self):
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        encrypted = encrypt_field(key1, "secret")
        with pytest.raises(Exception):
            decrypt_field(key2, encrypted)

    def test_tampered_ciphertext_fails(self):
        key = os.urandom(32)
        encrypted = encrypt_field(key, "secret")
        import base64
        raw = base64.b64decode(encrypted)
        tampered = bytearray(raw)
        tampered[-1] ^= 0xFF
        with pytest.raises(Exception):
            decrypt_field(key, base64.b64encode(bytes(tampered)).decode())


class TestHMACFingerprints:
    def test_deterministic(self):
        key = b"test-key"
        fp1 = hmac_fingerprint(key, "account-123")
        fp2 = hmac_fingerprint(key, "account-123")
        assert fp1 == fp2

    def test_different_data_different_fingerprint(self):
        key = b"test-key"
        fp1 = hmac_fingerprint(key, "account-123")
        fp2 = hmac_fingerprint(key, "account-456")
        assert fp1 != fp2

    def test_different_key_different_fingerprint(self):
        fp1 = hmac_fingerprint(b"key-1", "account-123")
        fp2 = hmac_fingerprint(b"key-2", "account-123")
        assert fp1 != fp2

    def test_uses_sha256(self):
        key = b"test"
        fp = hmac_fingerprint(key, "data")
        assert len(fp) == 64  # hex SHA-256 = 64 chars


class TestCanonicalSerialization:
    def test_sorted_keys(self):
        result = canonical_json({"z": 1, "a": 2})
        assert result == b'{"a":2,"z":1}'

    def test_no_whitespace(self):
        result = canonical_json({"key": "value", "nested": {"a": 1}})
        assert b" " not in result
        assert b"\n" not in result

    def test_deterministic_hash(self):
        h1 = canonical_hash({"b": 2, "a": 1})
        h2 = canonical_hash({"a": 1, "b": 2})
        assert h1 == h2


@pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC not available in this environment")
class TestMLDSA65:
    def test_sign_and_verify(self):
        from backend.trust.crypto import generate_mldsa65_keypair, sign_mldsa65, verify_mldsa65
        seed, pub = generate_mldsa65_keypair()
        data = b"post-quantum test"
        sig = sign_mldsa65(seed, data)
        assert verify_mldsa65(pub, sig, data)

    def test_invalid_signature_rejected(self):
        from backend.trust.crypto import generate_mldsa65_keypair, sign_mldsa65, verify_mldsa65
        seed, pub = generate_mldsa65_keypair()
        sig = sign_mldsa65(seed, b"data")
        tampered = bytearray(sig)
        tampered[10] ^= 0xFF
        assert not verify_mldsa65(pub, bytes(tampered), b"data")

    def test_tampered_data_rejected(self):
        from backend.trust.crypto import generate_mldsa65_keypair, sign_mldsa65, verify_mldsa65
        seed, pub = generate_mldsa65_keypair()
        sig = sign_mldsa65(seed, b"original")
        assert not verify_mldsa65(pub, sig, b"tampered")

    def test_wrong_key_rejected(self):
        from backend.trust.crypto import generate_mldsa65_keypair, sign_mldsa65, verify_mldsa65
        seed1, _ = generate_mldsa65_keypair()
        _, pub2 = generate_mldsa65_keypair()
        sig = sign_mldsa65(seed1, b"data")
        assert not verify_mldsa65(pub2, sig, b"data")


@pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC not available in this environment")
class TestHybridSignatures:
    def _mldsa_keys(self):
        from cryptography.hazmat.primitives.asymmetric import mldsa
        priv = mldsa.MLDSA65PrivateKey.generate()
        pub = priv.public_key()
        return priv, pub

    def test_hybrid_sign_verify(self):
        from backend.trust.crypto import hybrid_sign, hybrid_verify, HybridSignature
        ed_priv, ed_pub = generate_ed25519_keypair()
        mldsa_priv, mldsa_pub = self._mldsa_keys()
        data = b"hybrid test"
        sig = hybrid_sign(ed_priv, data, mldsa_private=mldsa_priv)
        assert isinstance(sig, HybridSignature)
        assert sig.mldsa_sig is not None
        assert hybrid_verify(ed_pub, data, sig, mldsa_public=mldsa_pub)

    def test_hybrid_rejects_tampered_ed25519(self):
        from backend.trust.crypto import hybrid_sign, hybrid_verify, HybridSignature
        ed_priv, ed_pub = generate_ed25519_keypair()
        mldsa_priv, mldsa_pub = self._mldsa_keys()
        sig = hybrid_sign(ed_priv, b"data", mldsa_private=mldsa_priv)
        # Tamper with Ed25519 signature
        import base64
        raw_ed = bytearray(base64.b64decode(sig.ed25519_sig))
        raw_ed[0] ^= 0xFF
        tampered = HybridSignature(
            ed25519_sig=base64.b64encode(bytes(raw_ed)).decode(),
            mldsa_sig=sig.mldsa_sig,
        )
        assert not hybrid_verify(ed_pub, b"data", tampered, mldsa_public=mldsa_pub)

    def test_hybrid_rejects_tampered_mldsa(self):
        from backend.trust.crypto import hybrid_sign, hybrid_verify, HybridSignature
        ed_priv, ed_pub = generate_ed25519_keypair()
        mldsa_priv, mldsa_pub = self._mldsa_keys()
        sig = hybrid_sign(ed_priv, b"data", mldsa_private=mldsa_priv)
        # Tamper with ML-DSA signature
        import base64
        raw_mldsa = bytearray(base64.b64decode(sig.mldsa_sig))
        raw_mldsa[10] ^= 0xFF
        tampered = HybridSignature(
            ed25519_sig=sig.ed25519_sig,
            mldsa_sig=base64.b64encode(bytes(raw_mldsa)).decode(),
        )
        assert not hybrid_verify(ed_pub, b"data", tampered, mldsa_public=mldsa_pub)

    def test_hybrid_requires_both_valid(self):
        """Hybrid verification must require BOTH signatures. Never silently downgrade."""
        from backend.trust.crypto import hybrid_sign, hybrid_verify, HybridSignature
        ed_priv, ed_pub = generate_ed25519_keypair()
        mldsa_priv, mldsa_pub = self._mldsa_keys()
        sig = hybrid_sign(ed_priv, b"data", mldsa_private=mldsa_priv)

        # Valid Ed25519 + no ML-DSA → must fail in required mode
        no_mldsa = HybridSignature(ed25519_sig=sig.ed25519_sig, mldsa_sig=None)
        assert not hybrid_verify(ed_pub, b"data", no_mldsa, mldsa_public=mldsa_pub, pqc_mode="required")

        # Corrupt ML-DSA but keep Ed25519 → must fail
        import base64
        bad_mldsa = base64.b64encode(b"\x00" * 100).decode()
        broken = HybridSignature(ed25519_sig=sig.ed25519_sig, mldsa_sig=bad_mldsa)
        assert not hybrid_verify(ed_pub, b"data", broken, mldsa_public=mldsa_pub)


@pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC not available in this environment")
class TestMLKEM768:
    def test_encapsulate_decapsulate(self):
        from backend.trust.crypto import generate_mlkem768_keypair, mlkem768_encapsulate, mlkem768_decapsulate
        seed, pub = generate_mlkem768_keypair()
        result = mlkem768_encapsulate(pub)
        shared_secret = mlkem768_decapsulate(seed, result.ciphertext)
        assert shared_secret == result.shared_secret
        assert len(shared_secret) == 32

    def test_wrong_key_produces_different_secret(self):
        from backend.trust.crypto import generate_mlkem768_keypair, mlkem768_encapsulate, mlkem768_decapsulate
        seed1, pub1 = generate_mlkem768_keypair()
        seed2, _ = generate_mlkem768_keypair()
        result = mlkem768_encapsulate(pub1)
        # Decapsulating with wrong key should produce different shared secret
        # (ML-KEM implicit rejection)
        wrong_secret = mlkem768_decapsulate(seed2, result.ciphertext)
        assert wrong_secret != result.shared_secret


@pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC not available in this environment")
class TestSignedExecutionReceipt:
    def test_tampered_receipt_rejected(self):
        """Verify that a tampered execution receipt fails signature verification."""
        from backend.trust.crypto import hybrid_sign, hybrid_verify
        from cryptography.hazmat.primitives.asymmetric import mldsa

        ed_priv, ed_pub = generate_ed25519_keypair()
        mldsa_priv = mldsa.MLDSA65PrivateKey.generate()
        mldsa_pub = mldsa_priv.public_key()

        receipt_data = canonical_json({
            "receipt_id": "test-receipt-001",
            "tool_call_id": "tc-001",
            "status": "executed",
            "result": {"payment_id": "pay-001"},
        })

        sig = hybrid_sign(ed_priv, receipt_data, mldsa_private=mldsa_priv)

        tampered_data = canonical_json({
            "receipt_id": "test-receipt-001",
            "tool_call_id": "tc-001",
            "status": "executed",
            "result": {"payment_id": "pay-TAMPERED"},
        })

        assert not hybrid_verify(ed_pub, tampered_data, sig, mldsa_public=mldsa_pub)
        assert hybrid_verify(ed_pub, receipt_data, sig, mldsa_public=mldsa_pub)


@pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC not available in this environment")
class TestKeyManager:
    def test_key_generation_and_caching(self):
        from backend.trust.key_manager import get_executor_keys, reset_keys
        reset_keys()
        keys1 = get_executor_keys()
        keys2 = get_executor_keys()
        assert keys1.ed25519_public == keys2.ed25519_public
        assert keys1.pqc_enabled is True
        reset_keys()

    def test_key_rotation(self):
        from backend.trust.key_manager import get_executor_keys, reset_keys
        reset_keys()
        keys_before = get_executor_keys()
        reset_keys()
        keys_after = get_executor_keys()
        # After reset, new keys are generated
        assert keys_before.ed25519_public != keys_after.ed25519_public
        reset_keys()
