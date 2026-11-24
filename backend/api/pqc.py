"""PQC API — post-quantum cryptography status and ML-KEM-768 demo."""
from __future__ import annotations

import base64
import time
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.auth import get_current_user, require_role
from backend.models.user import User
from backend.trust.crypto import (
    detect_pqc_capabilities,
    generate_mlkem768_keypair,
    mlkem768_decapsulate,
    mlkem768_encapsulate,
)
from backend.trust.key_manager import get_executor_keys

router = APIRouter()


class PQCStatusResponse(BaseModel):
    mldsa65_available: bool
    mlkem768_available: bool
    openssl_version: str
    executor_pqc_signing: bool
    executor_ed25519_public: str
    executor_mldsa_public: str | None


class MLKEMDemoResponse(BaseModel):
    public_key_b64: str
    ciphertext_b64: str
    shared_secret_match: bool
    shared_secret_length_bytes: int
    encapsulation_time_ms: float
    decapsulation_time_ms: float


@router.get("/status", response_model=PQCStatusResponse)
async def pqc_status(
    _user: Annotated[User, Depends(get_current_user)],
):
    caps = detect_pqc_capabilities()
    keys = get_executor_keys()
    return PQCStatusResponse(
        mldsa65_available=caps.mldsa_available,
        mlkem768_available=caps.mlkem_available,
        openssl_version=caps.openssl_version,
        executor_pqc_signing=keys.pqc_enabled,
        executor_ed25519_public=keys.ed25519_public_b64,
        executor_mldsa_public=keys.mldsa_public_b64,
    )


@router.post("/mlkem-demo", response_model=MLKEMDemoResponse)
async def mlkem_demo(
    _user: Annotated[User, Depends(require_role("security_admin"))],
):
    caps = detect_pqc_capabilities()
    if not caps.mlkem_available:
        from fastapi import HTTPException
        raise HTTPException(503, "ML-KEM-768 not available on this platform")

    priv, pub = generate_mlkem768_keypair()

    t0 = time.perf_counter()
    encap_result = mlkem768_encapsulate(pub)
    encap_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    decap_secret = mlkem768_decapsulate(priv, encap_result.ciphertext)
    decap_ms = (time.perf_counter() - t0) * 1000

    return MLKEMDemoResponse(
        public_key_b64=base64.b64encode(pub).decode("ascii"),
        ciphertext_b64=base64.b64encode(encap_result.ciphertext).decode("ascii"),
        shared_secret_match=(encap_result.shared_secret == decap_secret),
        shared_secret_length_bytes=len(decap_secret),
        encapsulation_time_ms=round(encap_ms, 3),
        decapsulation_time_ms=round(decap_ms, 3),
    )
