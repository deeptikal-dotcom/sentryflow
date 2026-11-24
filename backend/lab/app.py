"""Attack Simulation Lab — isolated environment for security testing."""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="SentryFlow Attack Lab", version="0.1.0")


@app.get("/api/v1/lab/health")
async def health():
    return {"status": "healthy", "service": "sentryflow-lab", "isolated": True}


@app.post("/api/v1/lab/reset")
async def reset_lab():
    return {"status": "reset", "message": "Lab environment reset - implementation pending"}


@app.get("/api/v1/lab/scenarios")
async def list_scenarios():
    return {
        "scenarios": [
            {"id": "pi-direct", "name": "Direct Prompt Injection", "category": "injection"},
            {"id": "pi-indirect", "name": "Indirect Prompt Injection via Document", "category": "injection"},
            {"id": "supplier-impersonation", "name": "Supplier Impersonation", "category": "fraud"},
            {"id": "invoice-duplication", "name": "Invoice Duplication Attack", "category": "fraud"},
            {"id": "bank-detail-fraud", "name": "Bank Detail Change Fraud", "category": "fraud"},
            {"id": "privilege-escalation", "name": "Agent Privilege Escalation", "category": "auth"},
            {"id": "approval-replay", "name": "Approval Replay Attack", "category": "auth"},
            {"id": "rate-limit-bypass", "name": "Rate Limit Bypass", "category": "dos"},
            {"id": "data-exfiltration", "name": "Data Exfiltration via Agent", "category": "data"},
            {"id": "multi-vector", "name": "Combined Multi-Vector Attack", "category": "advanced"},
        ]
    }
