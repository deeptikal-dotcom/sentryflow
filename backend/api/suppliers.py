"""Supplier management API — registry, verification, bank detail tracking."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user, require_role
from backend.audit.audit_logger import AuditLogger
from backend.database import get_session
from backend.models.supplier import Supplier, SupplierBankAccount
from backend.models.user import User

router = APIRouter()
audit = AuditLogger()


@router.get("/")
async def list_suppliers(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Supplier).order_by(Supplier.name))
    suppliers = result.scalars().all()
    return {
        "suppliers": [
            {
                "id": s.id,
                "name": s.name,
                "tax_id": s.tax_id,
                "verified": s.verified,
                "risk_score": s.risk_score,
                "created_at": s.created_at,
            }
            for s in suppliers
        ]
    }


@router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    bank_result = await session.execute(
        select(SupplierBankAccount)
        .where(SupplierBankAccount.supplier_id == supplier_id)
        .order_by(SupplierBankAccount.created_at.desc())
    )
    bank_accounts = bank_result.scalars().all()

    return {
        "id": supplier.id,
        "name": supplier.name,
        "tax_id": supplier.tax_id,
        "verified": supplier.verified,
        "risk_score": supplier.risk_score,
        "bank_accounts": [
            {
                "id": b.id,
                "bank_name": b.bank_name,
                "is_current": b.is_current,
                "account_fingerprint": b.account_number_hmac[:12] + "...",
                "created_at": b.created_at,
            }
            for b in bank_accounts
        ],
    }


@router.post("/{supplier_id}/verify")
async def verify_supplier(
    supplier_id: str,
    user: Annotated[User, Depends(require_role("security_admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    result = await session.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    from datetime import datetime, timezone
    supplier.verified = True
    supplier.verified_by = user.id
    supplier.updated_at = datetime.now(timezone.utc).isoformat()

    await audit.log(
        session, "supplier_verified", "user", user.id,
        f"verify:{supplier.name}",
        target_type="supplier", target_id=supplier_id,
    )
    await session.commit()
    return {"id": supplier_id, "verified": True}
