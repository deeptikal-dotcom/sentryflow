"""Payment System Simulator — payment queue, transaction ledger, idempotency.

All amounts are integer minor-currency units (cents).
The gateway owns: approval consumption, payment execution, financial ledger updates.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.payment import PaymentRequest, TransactionLedger


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


def compute_idempotency_key(
    invoice_id: str, supplier_id: str, amount_minor: int, currency: str
) -> str:
    data = f"{invoice_id}:{supplier_id}:{amount_minor}:{currency}"
    return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class PaymentResult:
    payment_id: str
    status: str
    transaction_ref: str | None
    error: str | None


class PaymentSimulator:

    async def create_payment_request(
        self,
        session: AsyncSession,
        invoice_id: str,
        supplier_id: str,
        bank_account_id: str,
        amount_minor: int,
        currency: str,
        requested_by_agent: str | None = None,
    ) -> PaymentResult:
        idem_key = compute_idempotency_key(
            invoice_id, supplier_id, amount_minor, currency
        )

        existing = await session.execute(
            select(PaymentRequest).where(
                PaymentRequest.idempotency_key == idem_key
            )
        )
        if existing.scalar_one_or_none():
            return PaymentResult(
                payment_id="",
                status="duplicate_rejected",
                transaction_ref=None,
                error="Duplicate payment request detected",
            )

        payment_id = _uuid()
        payment = PaymentRequest(
            id=payment_id,
            idempotency_key=idem_key,
            invoice_id=invoice_id,
            supplier_id=supplier_id,
            bank_account_id=bank_account_id,
            amount_minor=amount_minor,
            currency=currency,
            requested_by_agent=requested_by_agent,
            status="pending_approval",
            created_at=_now(),
        )
        session.add(payment)
        await session.flush()

        return PaymentResult(
            payment_id=payment_id,
            status="pending_approval",
            transaction_ref=None,
            error=None,
        )

    async def execute_payment(
        self,
        session: AsyncSession,
        payment_id: str,
        approval_id: str,
        executed_by: str,
    ) -> PaymentResult:
        result = await session.execute(
            select(PaymentRequest).where(PaymentRequest.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            return PaymentResult(
                payment_id=payment_id,
                status="failed",
                transaction_ref=None,
                error="Payment request not found",
            )

        if payment.status not in ("pending_approval", "approved"):
            return PaymentResult(
                payment_id=payment_id,
                status="failed",
                transaction_ref=None,
                error=f"Cannot execute payment in status: {payment.status}",
            )

        transaction_ref = f"TXN-{uuid.uuid4().hex[:12].upper()}"

        payment.status = "completed"
        payment.approval_id = approval_id
        payment.execution_ref = transaction_ref
        payment.executed_at = _now()

        ledger_entry = TransactionLedger(
            id=_uuid(),
            transaction_ref=transaction_ref,
            payment_request_id=payment_id,
            event_type="executed",
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            counterparty_id=payment.supplier_id,
            initiated_by=executed_by,
            recorded_at=_now(),
            details=json.dumps({
                "approval_id": approval_id,
                "bank_account_id": payment.bank_account_id,
            }),
        )
        session.add(ledger_entry)
        await session.flush()

        return PaymentResult(
            payment_id=payment_id,
            status="completed",
            transaction_ref=transaction_ref,
            error=None,
        )

    async def get_payment_status(
        self, session: AsyncSession, payment_id: str
    ) -> dict | None:
        result = await session.execute(
            select(PaymentRequest).where(PaymentRequest.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            return None
        return {
            "id": payment.id,
            "status": payment.status,
            "amount_minor": payment.amount_minor,
            "currency": payment.currency,
            "execution_ref": payment.execution_ref,
            "created_at": payment.created_at,
            "executed_at": payment.executed_at,
        }
