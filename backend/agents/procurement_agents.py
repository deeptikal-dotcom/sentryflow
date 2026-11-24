"""Five procurement agent types for SentryFlow.

Each agent processes domain-specific tasks and routes all actions
through the security gateway. No agent can bypass the gateway,
approve its own actions, or impersonate human identities.
"""
from __future__ import annotations

import logging

from backend.agents.base_agent import BaseAgent, ToolCall

logger = logging.getLogger("sentryflow.agents")


class BuyerAgent(BaseAgent):
    """Creates purchase orders from approved requisitions."""

    def __init__(self, agent_id: str, gateway_url: str = "http://gateway:8000"):
        super().__init__(
            agent_id=agent_id,
            agent_type="buyer",
            capabilities=["read_suppliers", "create_po", "read_contracts"],
            gateway_url=gateway_url,
        )

    async def process_task(self, task: dict) -> dict:
        supplier_id = task.get("supplier_id")
        items = task.get("items", [])

        check = await self.call_tool(ToolCall(
            tool_name="read_supplier",
            parameters={"supplier_id": supplier_id},
        ))
        if check.decision == "deny":
            return {"status": "failed", "reason": check.reason}

        total_minor = sum(i["quantity"] * i["unit_price_minor"] for i in items)

        result = await self.call_tool(ToolCall(
            tool_name="create_po",
            parameters={
                "supplier_id": supplier_id,
                "items": items,
                "total_amount_minor": total_minor,
                "currency": task.get("currency", "USD"),
            },
        ))

        return {
            "status": "submitted" if result.decision != "deny" else "denied",
            "tool_call_id": result.tool_call_id,
            "decision": result.decision,
            "approval_required": result.approval_required,
        }


class NegotiatorAgent(BaseAgent):
    """Analyzes contracts and suggests terms adjustments."""

    def __init__(self, agent_id: str, gateway_url: str = "http://gateway:8000"):
        super().__init__(
            agent_id=agent_id,
            agent_type="negotiator",
            capabilities=["read_contracts", "read_suppliers", "suggest_terms"],
            gateway_url=gateway_url,
        )

    async def process_task(self, task: dict) -> dict:
        contract_id = task.get("contract_id")

        result = await self.call_tool(ToolCall(
            tool_name="read_contract",
            parameters={"contract_id": contract_id},
        ))
        if result.decision == "deny":
            return {"status": "failed", "reason": result.reason}

        return {
            "status": "analyzed",
            "tool_call_id": result.tool_call_id,
            "analysis": "Contract terms reviewed through gateway",
        }


class InvoiceProcessorAgent(BaseAgent):
    """Processes incoming invoices — extraction, matching, validation."""

    def __init__(self, agent_id: str, gateway_url: str = "http://gateway:8000"):
        super().__init__(
            agent_id=agent_id,
            agent_type="invoice_processor",
            capabilities=["read_invoices", "process_invoices", "read_suppliers"],
            gateway_url=gateway_url,
        )

    async def process_task(self, task: dict) -> dict:
        document_id = task.get("document_id")
        invoice_text = task.get("invoice_text", "")

        result = await self.call_tool(ToolCall(
            tool_name="process_invoice",
            parameters={
                "document_id": document_id,
                "invoice_text": invoice_text,
            },
            context=invoice_text[:500] if invoice_text else None,
        ))

        return {
            "status": "processed" if result.decision != "deny" else "denied",
            "tool_call_id": result.tool_call_id,
            "decision": result.decision,
            "risk_score": result.risk_score,
            "approval_required": result.approval_required,
        }


class POManagerAgent(BaseAgent):
    """Manages purchase order lifecycle — approvals, receipts, updates."""

    def __init__(self, agent_id: str, gateway_url: str = "http://gateway:8000"):
        super().__init__(
            agent_id=agent_id,
            agent_type="po_manager",
            capabilities=["read_pos", "update_po_status", "read_receipts"],
            gateway_url=gateway_url,
        )

    async def process_task(self, task: dict) -> dict:
        po_id = task.get("po_id")
        action = task.get("action", "review")

        result = await self.call_tool(ToolCall(
            tool_name=f"{action}_po",
            parameters={"po_id": po_id},
        ))

        return {
            "status": "completed" if result.decision != "deny" else "denied",
            "tool_call_id": result.tool_call_id,
            "decision": result.decision,
        }


class PaymentAgent(BaseAgent):
    """Initiates payment requests for validated invoices."""

    def __init__(self, agent_id: str, gateway_url: str = "http://gateway:8000"):
        super().__init__(
            agent_id=agent_id,
            agent_type="payment",
            capabilities=["read_invoices", "create_payment", "read_suppliers"],
            gateway_url=gateway_url,
        )

    async def process_task(self, task: dict) -> dict:
        invoice_id = task.get("invoice_id")
        supplier_id = task.get("supplier_id")
        amount_minor = task.get("amount_minor")
        bank_account_id = task.get("bank_account_id")

        result = await self.call_tool(ToolCall(
            tool_name="create_payment",
            parameters={
                "invoice_id": invoice_id,
                "supplier_id": supplier_id,
                "amount_minor": amount_minor,
                "bank_account_id": bank_account_id,
                "currency": task.get("currency", "USD"),
            },
        ))

        return {
            "status": "payment_requested" if result.decision != "deny" else "denied",
            "tool_call_id": result.tool_call_id,
            "decision": result.decision,
            "approval_required": result.approval_required,
            "approval_id": result.approval_id,
        }


AGENT_REGISTRY = {
    "buyer": BuyerAgent,
    "negotiator": NegotiatorAgent,
    "invoice_processor": InvoiceProcessorAgent,
    "po_manager": POManagerAgent,
    "payment": PaymentAgent,
}
