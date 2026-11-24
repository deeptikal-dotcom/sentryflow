from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_suppliers():
    return {"suppliers": [], "message": "Supplier management - implementation pending"}
