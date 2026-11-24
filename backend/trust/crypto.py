"""Cryptographic operations for SentryFlow.

Provides Ed25519 signatures, AES-256-GCM field encryption, HMAC-SHA256 fingerprints,
and PQC probing (ML-DSA-65, ML-KEM-768) when available.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


@dataclass
class PQCCapabilities:
    mldsa_available: bool = False
    mlkem_available: bool = False
    openssl_version: str = ""


def detect_pqc_capabilities() -> PQCCapabilities:
    caps = PQCCapabilities()
    try:
        from cryptography.hazmat.backends.openssl.backend import backend
        caps.openssl_version = backend.openssl_version_text()
    except Exception:
        pass

    try:
        from cryptography.hazmat.primitives.asymmetric import mldsa
        _test_key = mldsa.MLDSA65PrivateKey.generate()
        caps.mldsa_available = True
    except Exception:
        pass

    try:
        from cryptography.hazmat.primitives.asymmetric import mlkem
        _test_key = mlkem.MLKEM768PrivateKey.generate()
        caps.mlkem_available = True
    except Exception:
        pass

    return caps


# --- ML-DSA-65 ---

def generate_mldsa65_keypair() -> tuple[bytes, bytes]:
    from cryptography.hazmat.primitives.asymmetric import mldsa
    private_key = mldsa.MLDSA65PrivateKey.generate()
    seed = private_key.private_bytes_raw()
    pub_bytes = private_key.public_key().public_bytes_raw()
    return seed, pub_bytes


def sign_mldsa65(seed: bytes, data: bytes) -> bytes:
    from cryptography.hazmat.primitives.asymmetric import mldsa
    private_key = mldsa.MLDSA65PrivateKey.from_seed_bytes(seed)
    return private_key.sign(data)


def verify_mldsa65(public_key_bytes: bytes, signature: bytes, data: bytes) -> bool:
    from cryptography.hazmat.primitives.asymmetric import mldsa
    public_key = mldsa.MLDSA65PublicKey.from_public_bytes(public_key_bytes)
    try:
        public_key.verify(signature, data)
        return True
    except Exception:
        return False


# --- ML-KEM-768 ---

@dataclass
class MLKEMEncapsulationResult:
    ciphertext: bytes
    shared_secret: bytes


def generate_mlkem768_keypair() -> tuple[bytes, bytes]:
    from cryptography.hazmat.primitives.asymmetric import mlkem
    private_key = mlkem.MLKEM768PrivateKey.generate()
    seed = private_key.private_bytes_raw()
    pub_bytes = private_key.public_key().public_bytes_raw()
    return seed, pub_bytes


def mlkem768_encapsulate(public_key_bytes: bytes) -> MLKEMEncapsulationResult:
    from cryptography.hazmat.primitives.asymmetric import mlkem
    public_key = mlkem.MLKEM768PublicKey.from_public_bytes(public_key_bytes)
    shared_secret, ciphertext = public_key.encapsulate()
    return MLKEMEncapsulationResult(ciphertext=ciphertext, shared_secret=shared_secret)


def mlkem768_decapsulate(seed: bytes, ciphertext: bytes) -> bytes:
    from cryptography.hazmat.primitives.asymmetric import mlkem
    private_key = mlkem.MLKEM768PrivateKey.from_seed_bytes(seed)
    return private_key.decapsulate(ciphertext)


# --- Ed25519 ---

def generate_ed25519_keypair() -> tuple[bytes, bytes]:
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()
    )
    public_bytes = private_key.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw
    )
    return private_bytes, public_bytes


def sign_ed25519(private_key_bytes: bytes, data: bytes) -> bytes:
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    return private_key.sign(data)


def verify_ed25519(public_key_bytes: bytes, signature: bytes, data: bytes) -> bool:
    public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        public_key.verify(signature, data)
        return True
    except Exception:
        return False


# --- AES-256-GCM field encryption ---

def encrypt_field(key: bytes, plaintext: str) -> str:
    if len(key) != 32:
        raise ValueError("AES-256 key must be 32 bytes")
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_field(key: bytes, ciphertext_b64: str) -> str:
    if len(key) != 32:
        raise ValueError("AES-256 key must be 32 bytes")
    raw = base64.b64decode(ciphertext_b64)
    nonce = raw[:12]
    ct = raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")


# --- HMAC-SHA256 fingerprints ---

def hmac_fingerprint(key: bytes, value: str) -> str:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


# --- Canonical serialization ---

def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def canonical_hash(data: Any) -> str:
    return hashlib.sha256(canonical_json(data)).hexdigest()


# --- Hybrid signatures (Ed25519 + ML-DSA-65 when available) ---

@dataclass
class HybridSignature:
    ed25519_sig: str  # base64
    mldsa_sig: str | None = None  # base64, None when PQC unavailable


def hybrid_sign(
    ed25519_private: bytes,
    data: bytes,
    mldsa_private: Any | None = None,
    pqc_mode: str = "optional",
) -> HybridSignature:
    ed_sig = sign_ed25519(ed25519_private, data)
    result = HybridSignature(ed25519_sig=base64.b64encode(ed_sig).decode("ascii"))

    if mldsa_private is not None:
        try:
            mldsa_sig = mldsa_private.sign(data)
            result.mldsa_sig = base64.b64encode(mldsa_sig).decode("ascii")
        except Exception:
            if pqc_mode == "required":
                raise
    elif pqc_mode == "required":
        raise RuntimeError("ML-DSA-65 signing required but no key provided")

    return result


def hybrid_verify(
    ed25519_public: bytes,
    data: bytes,
    signature: HybridSignature,
    mldsa_public: Any | None = None,
    pqc_mode: str = "optional",
) -> bool:
    ed_sig = base64.b64decode(signature.ed25519_sig)
    if not verify_ed25519(ed25519_public, ed_sig, data):
        return False

    if signature.mldsa_sig is not None:
        if mldsa_public is None:
            return False
        try:
            mldsa_sig = base64.b64decode(signature.mldsa_sig)
            mldsa_public.verify(mldsa_sig, data)
        except Exception:
            return False
    elif pqc_mode == "required":
        return False

    return True
