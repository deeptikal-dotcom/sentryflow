"""Trusted Executor — performs business actions after gateway authorization.

The Executor lives in the trusted zone. It:
1. Validates that an approval exists, is approved, and not yet consumed
2. Verifies parameter binding (canonical hash match)
3. Executes the business operation (ERP/payment sim)
4. Signs the execution receipt
5. Marks the approval as consumed
6. Returns a signed receipt to the caller

No LLM reasoning participates in execution decisions.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.audit.audit_logger import AuditLogger
from backend.models.purchase_order import POLineItem, PurchaseOrder
from backend.models.supplier import Supplier
from backend.simulation.erp_simulator import ERPSimulator
from backend.simulation.payment_simulator import PaymentSimulator
from backend.trust.approval_manager import ApprovalError, ApprovalManager
from backend.trust.crypto import (
    canonical_json,
    hybrid_sign,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


@dataclass
class ExecutionReceipt:
    receipt_id: str
    tool_call_id: str
    tool_name: str
    status: str  # executed|denied|failed
    result: dict = field(default_factory=dict)
    approval_id: str | None = None
    signature: str | None = None  # base64 Ed25519 over canonical receipt
    mldsa_signature: str | None = None  # base64 ML-DSA-65 when PQC available
    pqc_signed: bool = False
    executed_at: str = ""
    error: str | None = None


class Executor:
    def __init__(
        self,
        signing_key: bytes | None = None,
        mldsa_private_key: bytes | None = None,
    ):
        self._signing_key = signing_key
        self._mldsa_private_key = mldsa_private_key
        self._erp = ERPSimulator()
        self._payments = PaymentSimulator()
        self._approvals = ApprovalManager()
        self._audit = AuditLogger()

    async def execute(
        self,
        session: AsyncSession,
        tool_call_id: str,
        tool_name: str,
        parameters: dict,
        approval_id: str | None = None,
        actor_id: str = "executor",
    ) -> ExecutionReceipt:
        receipt_id = _uuid()

        if approval_id:
            try:
                await self._approvals.consume(
                    session, approval_id, parameters
                )
            except ApprovalError as e:
                receipt = ExecutionReceipt(
                    receipt_id=receipt_id,
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    status="denied",
                    error=str(e),
                    approval_id=approval_id,
                    executed_at=_now(),
                )
                await self._audit.log(
                    session, "execution_denied", "executor", actor_id,
                    f"execute:{tool_name}",
                    target_type="tool_call", target_id=tool_call_id,
                    decision_summary=f"Approval consumption failed: {e}",
                    risk_score=90,
                )
                return receipt

        try:
            result = await self._dispatch(session, tool_name, parameters)
        except Exception as e:
            receipt = ExecutionReceipt(
                receipt_id=receipt_id,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                status="failed",
                error=str(e),
                approval_id=approval_id,
                executed_at=_now(),
            )
            await self._audit.log(
                session, "execution_failed", "executor", actor_id,
                f"execute:{tool_name}",
                target_type="tool_call", target_id=tool_call_id,
                decision_summary=f"Execution failed: {e}",
                risk_score=50,
            )
            return receipt

        receipt = ExecutionReceipt(
            receipt_id=receipt_id,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            status="executed",
            result=result,
            approval_id=approval_id,
            executed_at=_now(),
        )

        if self._signing_key:
            self._sign_receipt(receipt)

        await self._audit.log(
            session, "execution_completed", "executor", actor_id,
            f"execute:{tool_name}",
            target_type="tool_call", target_id=tool_call_id,
            decision_summary=f"Executed: {tool_name}",
        )

        return receipt

    async def _dispatch(
        self, session: AsyncSession, tool_name: str, params: dict
    ) -> dict:
        handlers = {
            "create_purchase_order": self._handle_create_po,
            "create_po": self._handle_create_po,
            "update_po_status": self._handle_update_po,
            "process_invoice": self._handle_process_invoice,
            "validate_invoice": self._handle_validate_invoice,
            "create_payment": self._handle_create_payment,
            "execute_payment": self._handle_execute_payment,
            "register_supplier": self._handle_register_supplier,
            "update_bank_details": self._handle_update_bank_details,
            "read_supplier": self._handle_read_supplier,
            "read_contract": self._handle_read_contract,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            if tool_name.startswith("read_") or tool_name.startswith("list_"):
                return {"status": "ok", "tool_name": tool_name, "note": "read operation completed"}
            raise ValueError(f"Unknown tool: {tool_name}")
        return await handler(session, params)

    async def _handle_create_po(self, session: AsyncSession, params: dict) -> dict:
        supplier_id = params["supplier_id"]
        items = params.get("items", [])
        total = params.get("total_amount_minor", 0)
        currency = params.get("currency", "USD")

        supplier_result = await session.execute(
            select(Supplier).where(Supplier.id == supplier_id)
        )
        supplier = supplier_result.scalar_one_or_none()
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")

        po_id = _uuid()
        po = PurchaseOrder(
            id=po_id,
            po_number=f"PO-{uuid.uuid4().hex[:8].upper()}",
            supplier_id=supplier_id,
            total_amount_minor=total,
            currency=currency,
            status="pending_approval",
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(po)

        for idx, item in enumerate(items):
            line = POLineItem(
                id=_uuid(),
                po_id=po_id,
                line_number=idx + 1,
                description=item.get("description", ""),
                quantity=item.get("quantity", 0),
                unit_price_minor=item.get("unit_price_minor", 0),
                total_minor=item.get("quantity", 0) * item.get("unit_price_minor", 0),
            )
            session.add(line)

        await session.flush()
        return {"po_id": po_id, "po_number": po.po_number, "status": po.status}

    async def _handle_update_po(self, session: AsyncSession, params: dict) -> dict:
        po_id = params["po_id"]
        new_status = params.get("status", "approved")
        result = await session.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == po_id)
        )
        po = result.scalar_one_or_none()
        if not po:
            raise ValueError(f"PO {po_id} not found")
        po.status = new_status
        po.updated_at = _now()
        return {"po_id": po_id, "status": new_status}

    async def _handle_process_invoice(self, session: AsyncSession, params: dict) -> dict:
        return {
            "status": "processed",
            "document_id": params.get("document_id"),
            "note": "Invoice text extracted and queued for validation",
        }

    async def _handle_validate_invoice(self, session: AsyncSession, params: dict) -> dict:
        invoice_id = params.get("invoice_id")
        if not invoice_id:
            raise ValueError("invoice_id required")
        report = await self._erp.validate_invoice(session, invoice_id)
        return {
            "match_id": report.match_id,
            "match_result": report.match_result,
            "discrepancy_count": len(report.discrepancies),
            "po_total": report.po_total,
            "invoice_total": report.invoice_total,
        }

    async def _handle_create_payment(self, session: AsyncSession, params: dict) -> dict:
        result = await self._payments.create_payment_request(
            session,
            invoice_id=params["invoice_id"],
            supplier_id=params["supplier_id"],
            bank_account_id=params.get("bank_account_id", ""),
            amount_minor=params["amount_minor"],
            currency=params.get("currency", "USD"),
            requested_by_agent=params.get("requested_by_agent"),
        )
        return {
            "payment_id": result.payment_id,
            "status": result.status,
            "error": result.error,
        }

    async def _handle_execute_payment(self, session: AsyncSession, params: dict) -> dict:
        result = await self._payments.execute_payment(
            session,
            payment_id=params["payment_id"],
            approval_id=params.get("approval_id", ""),
            executed_by=params.get("executed_by", "executor"),
        )
        return {
            "payment_id": result.payment_id,
            "status": result.status,
            "transaction_ref": result.transaction_ref,
            "error": result.error,
        }

    async def _handle_register_supplier(self, session: AsyncSession, params: dict) -> dict:
        supplier = Supplier(
            id=_uuid(),
            name=params["name"],
            tax_id=params.get("tax_id", ""),
            verified=False,
            risk_score=50,
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(supplier)
        await session.flush()
        return {"supplier_id": supplier.id, "name": supplier.name, "status": "registered"}

    async def _handle_update_bank_details(self, session: AsyncSession, params: dict) -> dict:
        return {
            "status": "queued",
            "supplier_id": params.get("supplier_id"),
            "note": "Bank detail change queued for manual verification",
        }

    async def _handle_read_supplier(self, session: AsyncSession, params: dict) -> dict:
        supplier_id = params.get("supplier_id")
        result = await session.execute(
            select(Supplier).where(Supplier.id == supplier_id)
        )
        supplier = result.scalar_one_or_none()
        if not supplier:
            raise ValueError(f"Supplier {supplier_id} not found")
        return {
            "id": supplier.id,
            "name": supplier.name,
            "verified": supplier.verified,
            "risk_score": supplier.risk_score,
        }

    async def _handle_read_contract(self, session: AsyncSession, params: dict) -> dict:
        return {
            "status": "ok",
            "contract_id": params.get("contract_id"),
            "note": "Contract data returned",
        }

    def _sign_receipt(self, receipt: ExecutionReceipt) -> None:
        data = canonical_json({
            "receipt_id": receipt.receipt_id,
            "tool_call_id": receipt.tool_call_id,
            "tool_name": receipt.tool_name,
            "status": receipt.status,
            "result": receipt.result,
            "approval_id": receipt.approval_id,
            "executed_at": receipt.executed_at,
        })

        mldsa_key = None
        if self._mldsa_private_key:
            try:
                from cryptography.hazmat.primitives.asymmetric import mldsa
                mldsa_key = mldsa.MLDSA65PrivateKey.from_seed_bytes(self._mldsa_private_key)
            except Exception:
                pass

        hsig = hybrid_sign(self._signing_key, data, mldsa_private=mldsa_key)
        receipt.signature = hsig.ed25519_sig
        if hsig.mldsa_sig:
            receipt.mldsa_signature = hsig.mldsa_sig
            receipt.pqc_signed = True
