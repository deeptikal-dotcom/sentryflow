"""Synthetic data generator for SentryFlow.

Creates realistic procurement data: suppliers, POs, goods receipts,
invoices, contracts — all with integer minor-currency units.
"""
from __future__ import annotations

import hashlib
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from sqlalchemy import select

from backend.database import async_session_factory, init_db
from backend.models.agent import Agent
from backend.models.contract import Contract
from backend.models.goods_receipt import GoodsReceipt, GRLineItem
from backend.models.invoice import Invoice, InvoiceLineItem
from backend.models.purchase_order import POLineItem, PurchaseOrder
from backend.models.supplier import Supplier, SupplierBankAccount
from backend.models.user import User
from backend.trust.crypto import (
    encrypt_field,
    generate_ed25519_keypair,
    hmac_fingerprint,
)

ph = PasswordHasher()

SUPPLIER_NAMES = [
    "Acme Industrial Supply Co.",
    "Global Tech Components Ltd.",
    "Pacific Rim Electronics",
    "Midwest Manufacturing Inc.",
    "Atlantic Logistics Solutions",
    "Summit Office Supplies",
    "Precision Engineering Corp.",
    "Riverside Chemical Group",
    "National Steel Distributors",
    "Western Safety Equipment",
    "Eastside Packaging Solutions",
    "Metro IT Services",
    "Continental Raw Materials",
    "Pioneer Construction Supply",
    "Valley Agricultural Products",
    "Harbor Shipping & Freight",
    "Central Medical Supplies",
    "Northern Energy Systems",
    "Southern Textile Mills",
    "Great Lakes Tool & Die",
]

PRODUCT_CATALOG = [
    ("Industrial ball bearings", 2500),
    ("Steel hex bolts (box/100)", 4500),
    ("Copper wire spool (500m)", 18500),
    ("Safety goggles (pack/12)", 7200),
    ("Hydraulic pump assembly", 145000),
    ("LED panel lights (box/10)", 32000),
    ("Thermal insulation roll", 8900),
    ("Circuit board (custom PCB)", 15600),
    ("Welding electrode rods (kg)", 3200),
    ("Stainless steel pipe (3m)", 12400),
    ("Office paper (box/5000)", 4500),
    ("Printer toner cartridge", 8900),
    ("Ergonomic desk chair", 42500),
    ("Network switch (24-port)", 65000),
    ("Server rack mount (42U)", 185000),
    ("Forklift battery", 95000),
    ("Air compressor filter", 2800),
    ("Conveyor belt (10m)", 78000),
    ("Fire extinguisher (ABC)", 6500),
    ("PPE coveralls (box/50)", 15500),
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _past_date(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _future_date(days_ahead: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()


def _get_encryption_key() -> bytes:
    key_hex = os.environ.get("FIELD_ENCRYPTION_KEY", "0" * 64)
    return bytes.fromhex(key_hex)


def _get_fingerprint_key() -> bytes:
    return os.environ.get("BANK_FINGERPRINT_KEY", "default-dev-fingerprint-key").encode()


async def generate_all():
    """Generate all synthetic data."""
    await init_db()

    enc_key = _get_encryption_key()
    fp_key = _get_fingerprint_key()

    async with async_session_factory() as session:
        existing = await session.execute(select(Supplier).limit(1))
        if existing.scalar_one_or_none():
            print("Data already exists. Skipping generation.")
            return

        rng = random.Random(42)

        users = await _create_users(session, rng)
        agents = await _create_agents(session, users, rng)
        suppliers = await _create_suppliers(session, users, enc_key, fp_key, rng)
        contracts = await _create_contracts(session, suppliers, users, rng)
        pos, po_lines = await _create_purchase_orders(session, suppliers, contracts, agents, users, rng)
        receipts = await _create_goods_receipts(session, pos, po_lines, users, rng)
        await _create_invoices(session, suppliers, pos, po_lines, receipts, agents, enc_key, fp_key, rng)

        await session.commit()
        print("Synthetic data generated successfully.")
        print(f"  Users: {len(users)}")
        print(f"  Agents: {len(agents)}")
        print(f"  Suppliers: {len(suppliers)}")
        print(f"  Contracts: {len(contracts)}")
        print(f"  Purchase Orders: {len(pos)}")
        print(f"  Goods Receipts: {len(receipts)}")


async def _create_users(session, rng) -> list[User]:
    users = []
    specs = [
        ("ops_manager", "procurement_operator", "Operations Manager"),
        ("finance_lead", "finance_approver", "Finance Lead"),
        ("security_analyst", "security_analyst", "Security Analyst"),
        ("auditor", "auditor", "Internal Auditor"),
        ("procurement_1", "procurement_operator", "Procurement Specialist"),
    ]
    now = _utcnow()
    for username, role, display_name in specs:
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=ph.hash("demo-password-" + username),
            role=role,
            display_name=display_name,
            active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        users.append(user)
    return users


async def _create_agents(session, users, rng) -> list[Agent]:
    agents = []
    specs = [
        ("buyer-agent", "buyer", ["list_suppliers", "compare_suppliers", "create_purchase_order"]),
        ("negotiator-agent", "negotiator", ["list_suppliers", "get_contract", "negotiate_terms"]),
        ("invoice-processor", "invoice_processor", ["process_invoice", "validate_invoice", "match_invoice"]),
        ("po-manager", "po_manager", ["create_purchase_order", "update_po_status", "receive_goods"]),
        ("payment-agent", "payment_approver", ["create_payment", "check_payment_status"]),
    ]
    admin = users[0]
    now = _utcnow()

    for name, agent_type, capabilities in specs:
        priv, pub = generate_ed25519_keypair()
        import base64
        agent = Agent(
            id=str(uuid.uuid4()),
            name=name,
            agent_type=agent_type,
            public_key_ed25519=base64.b64encode(pub).decode("ascii"),
            capabilities=str(capabilities),
            status="active",
            registered_by=admin.id,
            created_at=now,
            updated_at=now,
        )
        session.add(agent)
        agents.append(agent)
    return agents


async def _create_suppliers(session, users, enc_key, fp_key, rng) -> list[Supplier]:
    suppliers = []
    admin = users[0]
    now = _utcnow()

    for i, name in enumerate(SUPPLIER_NAMES):
        supplier = Supplier(
            id=str(uuid.uuid4()),
            name=name,
            tax_id=f"TAX-{rng.randint(100000, 999999)}",
            verified=i < 15,
            verified_by=admin.id if i < 15 else None,
            risk_score=rng.randint(10, 40) if i < 15 else rng.randint(40, 80),
            created_at=_past_date(rng.randint(30, 365)),
            updated_at=now,
        )
        session.add(supplier)
        suppliers.append(supplier)

        acct_num = f"{rng.randint(1000000000, 9999999999)}"
        routing = f"{rng.randint(100000000, 999999999)}"
        bank_account = SupplierBankAccount(
            id=str(uuid.uuid4()),
            supplier_id=supplier.id,
            bank_name=rng.choice(["First National Bank", "Global Commerce Bank", "Pacific Trust", "Metro Credit Union"]),
            account_number_hmac=hmac_fingerprint(fp_key, acct_num),
            routing_number_hmac=hmac_fingerprint(fp_key, routing),
            account_number_encrypted=encrypt_field(enc_key, acct_num),
            routing_number_encrypted=encrypt_field(enc_key, routing),
            is_current=True,
            changed_by=admin.id,
            created_at=_past_date(rng.randint(30, 365)),
        )
        session.add(bank_account)

    return suppliers


async def _create_contracts(session, suppliers, users, rng) -> list[Contract]:
    contracts = []
    admin = users[0]

    for i in range(10):
        supplier = suppliers[i]
        total = rng.randint(100_000_00, 5_000_000_00)
        contract = Contract(
            id=str(uuid.uuid4()),
            contract_number=f"CTR-2026-{i+1:04d}",
            supplier_id=supplier.id,
            effective_date=_past_date(rng.randint(30, 180)),
            expiry_date=_future_date(rng.randint(90, 365)),
            terms=str({"payment_terms": "NET30", "delivery": "FOB Destination"}),
            total_value_minor=total,
            currency="USD",
            status="active",
            content_hash=hashlib.sha256(f"contract-{i}".encode()).hexdigest(),
            created_by=admin.id,
            created_at=_past_date(rng.randint(30, 180)),
            updated_at=_utcnow(),
        )
        session.add(contract)
        contracts.append(contract)
    return contracts


async def _create_purchase_orders(session, suppliers, contracts, agents, users, rng):
    pos = []
    all_lines = {}

    buyer = agents[0]
    approver = users[1]

    for i in range(50):
        supplier = rng.choice(suppliers[:15])
        contract = contracts[i % len(contracts)] if i < 20 else None

        lines = []
        total = 0
        num_lines = rng.randint(1, 5)
        for ln in range(num_lines):
            product, base_price = rng.choice(PRODUCT_CATALOG)
            qty = rng.randint(1, 100)
            unit_price = base_price + rng.randint(-500, 500)
            line_total = qty * unit_price
            total += line_total
            lines.append((product, qty, unit_price, line_total))

        po = PurchaseOrder(
            id=str(uuid.uuid4()),
            po_number=f"PO-2026-{i+1:04d}",
            supplier_id=supplier.id,
            contract_id=contract.id if contract else None,
            total_amount_minor=total,
            currency="USD",
            status=rng.choice(["approved", "partially_received", "fulfilled"]),
            created_by_agent=buyer.id,
            approved_by=approver.id,
            created_at=_past_date(rng.randint(5, 90)),
            updated_at=_utcnow(),
        )
        session.add(po)
        pos.append(po)

        po_line_items = []
        for ln_idx, (desc, qty, unit_price, line_total) in enumerate(lines):
            line = POLineItem(
                id=str(uuid.uuid4()),
                po_id=po.id,
                line_number=ln_idx + 1,
                description=desc,
                quantity=qty,
                unit_price_minor=unit_price,
                total_minor=line_total,
                received_qty=qty if po.status in ("partially_received", "fulfilled") else 0,
            )
            session.add(line)
            po_line_items.append(line)
        all_lines[po.id] = po_line_items

    return pos, all_lines


async def _create_goods_receipts(session, pos, po_lines, users, rng):
    receipts = []
    receiver = users[0]

    for po in pos[:30]:
        lines = po_lines.get(po.id, [])
        if not lines:
            continue

        receipt = GoodsReceipt(
            id=str(uuid.uuid4()),
            receipt_number=f"GR-2026-{len(receipts)+1:04d}",
            po_id=po.id,
            supplier_id=po.supplier_id,
            received_by=receiver.id,
            status="confirmed",
            created_at=_past_date(rng.randint(1, 30)),
        )
        session.add(receipt)
        receipts.append(receipt)

        for po_line in lines:
            gr_line = GRLineItem(
                id=str(uuid.uuid4()),
                receipt_id=receipt.id,
                po_line_id=po_line.id,
                quantity_received=po_line.quantity,
                condition="acceptable",
            )
            session.add(gr_line)

    return receipts


async def _create_invoices(session, suppliers, pos, po_lines, receipts, agents, enc_key, fp_key, rng):
    processor = agents[2]

    for i, po in enumerate(pos[:40]):
        supplier = next((s for s in suppliers if s.id == po.supplier_id), None)
        if not supplier:
            continue

        lines = po_lines.get(po.id, [])
        total = sum(l.total_minor for l in lines)

        # 10% of invoices have small discrepancies (testing fraud detection)
        if rng.random() < 0.10:
            total += rng.randint(100, 50000)

        inv = Invoice(
            id=str(uuid.uuid4()),
            invoice_number=f"INV-{rng.randint(10000, 99999)}",
            supplier_id=supplier.id,
            po_id=po.id,
            total_amount_minor=total,
            currency="USD",
            content_hash=hashlib.sha256(f"invoice-{i}".encode()).hexdigest(),
            validation_status=rng.choice(["valid", "valid", "valid", "suspicious"]),
            status=rng.choice(["validated", "approved", "paid", "processing"]),
            processed_by_agent=processor.id,
            created_at=_past_date(rng.randint(1, 30)),
            updated_at=_utcnow(),
        )
        session.add(inv)

        for ln_idx, po_line in enumerate(lines):
            inv_line = InvoiceLineItem(
                id=str(uuid.uuid4()),
                invoice_id=inv.id,
                line_number=ln_idx + 1,
                description=po_line.description,
                quantity=po_line.quantity,
                unit_price_minor=po_line.unit_price_minor,
                total_minor=po_line.total_minor,
                po_line_id=po_line.id,
                match_status="matched" if inv.validation_status == "valid" else "discrepancy",
            )
            session.add(inv_line)
