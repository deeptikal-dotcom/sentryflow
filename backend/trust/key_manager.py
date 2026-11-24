"""Key manager for executor signing keys.

Generates and caches Ed25519 + ML-DSA-65 keypairs for the trusted executor.
Keys are stored in memory for the process lifetime and regenerated on restart.
Production deployment would use an HSM or KMS; this is the MVP key store.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass

from backend.trust.crypto import (
    detect_pqc_capabilities,
    generate_ed25519_keypair,
    generate_mldsa65_keypair,
)


@dataclass
class ExecutorKeys:
    ed25519_private: bytes
    ed25519_public: bytes
    mldsa_private: bytes | None = None
    mldsa_public: bytes | None = None
    pqc_enabled: bool = False

    @property
    def ed25519_public_b64(self) -> str:
        return base64.b64encode(self.ed25519_public).decode("ascii")

    @property
    def mldsa_public_b64(self) -> str | None:
        if self.mldsa_public is None:
            return None
        return base64.b64encode(self.mldsa_public).decode("ascii")


_cached_keys: ExecutorKeys | None = None


def get_executor_keys() -> ExecutorKeys:
    global _cached_keys
    if _cached_keys is not None:
        return _cached_keys

    ed_priv, ed_pub = generate_ed25519_keypair()
    keys = ExecutorKeys(ed25519_private=ed_priv, ed25519_public=ed_pub)

    caps = detect_pqc_capabilities()
    if caps.mldsa_available:
        mldsa_priv, mldsa_pub = generate_mldsa65_keypair()
        keys.mldsa_private = mldsa_priv
        keys.mldsa_public = mldsa_pub
        keys.pqc_enabled = True

    _cached_keys = keys
    return keys


def reset_keys() -> None:
    global _cached_keys
    _cached_keys = None
