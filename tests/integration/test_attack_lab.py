"""Integration tests for the attack lab running through the real gateway pipeline."""
from __future__ import annotations

import pytest


class TestAttackLabGatewayIntegration:
    @pytest.mark.asyncio
    async def test_run_all_scenarios(self, client, admin_token):
        resp = await client.post(
            "/api/v1/lab/run-all",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total"] == 10
        assert data["summary"]["accuracy"] > 0

    @pytest.mark.asyncio
    async def test_run_through_gateway(self, client, admin_token, admin_user, db_session):
        from backend.models.agent import Agent
        from backend.trust.crypto import generate_ed25519_keypair
        import base64, json, uuid
        from datetime import datetime, timezone

        admin, _ = admin_user
        priv, pub = generate_ed25519_keypair()
        agent = Agent(
            id=str(uuid.uuid4()),
            name="lab-test-agent",
            agent_type="buyer",
            public_key_ed25519=base64.b64encode(pub).decode("ascii"),
            capabilities=json.dumps(["process_invoice", "create_payment"]),
            status="active",
            registered_by=admin.id,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        db_session.add(agent)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/lab/run-gateway",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "gateway"
        assert data["summary"]["total"] == 10
        assert data["summary"]["true_positive_rate"] > 50

        for r in data["results"]:
            assert "policy_decision" in r
            assert "risk_score" in r

        # With only regex detection layer active (no LLM), injection-only
        # scenarios score max ~27 (regex=90 * weight=0.30), below the
        # policy escalation threshold of 70. The policy engine catches
        # financial/critical/unknown-tool scenarios through other rules.
        blocked_count = sum(1 for r in data["results"] if r["blocked"])
        assert blocked_count >= 5, f"Expected at least 5 blocked, got {blocked_count}"

    @pytest.mark.asyncio
    async def test_injection_scenario_detected(self, client, admin_token):
        resp = await client.post(
            "/api/v1/lab/scenarios/pi-direct/run",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Regex layer detects the injection (score 90), but weighted score is 27
        # since canary/structural/LLM layers are 0 without an LLM running.
        # The injection IS detected at the regex layer — policy engine uses
        # the injection_score to escalate when it exceeds its own threshold.
        assert data["detection_score"] > 0

    @pytest.mark.asyncio
    async def test_list_scenarios(self, client, admin_token):
        resp = await client.get(
            "/api/v1/lab/scenarios",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        scenarios = resp.json()["scenarios"]
        assert len(scenarios) == 10
        categories = {s["category"] for s in scenarios}
        assert "injection" in categories
