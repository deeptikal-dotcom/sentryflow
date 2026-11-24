"""Security invariant tests — these must ALWAYS pass.

Each test maps to a specific security invariant from the architecture.
Failure of any test means the system's security guarantees are broken.
"""
from __future__ import annotations

import pytest

from backend.trust.policy_engine import PolicyDecision, PolicyEngine, ToolCallContext


@pytest.fixture
def engine():
    return PolicyEngine()


def _make_ctx(**overrides) -> ToolCallContext:
    defaults = {
        "agent_id": "agent-001",
        "agent_status": "active",
        "agent_capabilities": ["list_suppliers", "process_invoice"],
        "tool_name": "list_suppliers",
        "classification": "read_only",
        "parameters": {},
        "amount_minor": None,
        "injection_score": 0,
        "session_id": "session-001",
    }
    defaults.update(overrides)
    return ToolCallContext(**defaults)


class TestSI1_DocumentsCannotGrantPermissions:
    """SI-1: Untrusted documents cannot grant permissions."""

    def test_injection_in_context_escalates(self, engine):
        ctx = _make_ctx(
            tool_name="create_payment",
            classification="financial",
            injection_score=75,
        )
        result = engine.evaluate(ctx)
        assert result.decision != PolicyDecision.ALLOW

    def test_high_injection_score_never_auto_allows(self, engine):
        ctx = _make_ctx(
            tool_name="list_suppliers",
            classification="read_only",
            injection_score=95,
        )
        result = engine.evaluate(ctx)
        assert result.decision == PolicyDecision.ESCALATE


class TestSI2_AgentsCannotBypassGateway:
    """SI-2: Agents cannot bypass the security gateway."""

    def test_suspended_agent_denied(self, engine):
        ctx = _make_ctx(
            agent_status="suspended",
            classification="read_only",
        )
        result = engine.evaluate(ctx)
        assert result.decision == PolicyDecision.DENY

    def test_revoked_agent_denied(self, engine):
        ctx = _make_ctx(
            agent_status="revoked",
            classification="financial",
        )
        result = engine.evaluate(ctx)
        assert result.decision == PolicyDecision.DENY

    def test_agent_without_capability_denied_for_write(self, engine):
        ctx = _make_ctx(
            tool_name="update_supplier",
            classification="write",
            agent_capabilities=["list_suppliers"],
        )
        result = engine.evaluate(ctx)
        assert result.decision != PolicyDecision.ALLOW


class TestSI3_AgentClaimsCannotAuthorize:
    """SI-3: Agent-generated claims cannot serve as authorization."""

    def test_financial_always_requires_human(self, engine):
        ctx = _make_ctx(
            tool_name="create_payment",
            classification="financial",
            parameters={"pre_approved": True, "approved_by": "cfo@company.com"},
        )
        result = engine.evaluate(ctx)
        assert result.decision == PolicyDecision.ESCALATE
        assert result.required_role is not None

    def test_critical_always_requires_admin(self, engine):
        ctx = _make_ctx(
            tool_name="modify_policy",
            classification="critical",
        )
        result = engine.evaluate(ctx)
        assert result.decision == PolicyDecision.ESCALATE
        assert result.required_role == "security_admin"


class TestSI4_FinancialFailClosed:
    """SI-4: Financial actions fail closed on auth failure."""

    def test_financial_never_auto_allowed(self, engine):
        ctx = _make_ctx(
            tool_name="create_payment",
            classification="financial",
            amount_minor=50000,
        )
        result = engine.evaluate(ctx)
        assert result.decision != PolicyDecision.ALLOW

    def test_no_matching_rule_defaults_deny(self, engine):
        ctx = _make_ctx(
            tool_name="unknown_tool_xyz",
            classification="unknown_classification",
        )
        result = engine.evaluate(ctx)
        assert result.decision == PolicyDecision.DENY

    def test_default_deny_has_reason(self, engine):
        ctx = _make_ctx(
            tool_name="unknown_tool",
            classification="unknown",
        )
        result = engine.evaluate(ctx)
        assert result.reason is not None


class TestSI7_HighRiskRequiresHumanAuth:
    """SI-7: High-risk actions require independent human authorization."""

    def test_high_amount_escalates(self, engine):
        ctx = _make_ctx(
            tool_name="create_payment",
            classification="financial",
            amount_minor=5_000_000,  # $50,000
        )
        result = engine.evaluate(ctx)
        assert result.decision == PolicyDecision.ESCALATE

    def test_bank_detail_change_escalates(self, engine):
        ctx = _make_ctx(
            tool_name="update_bank_details",
            classification="write",
        )
        result = engine.evaluate(ctx)
        assert result.decision == PolicyDecision.ESCALATE
        assert result.required_role == "finance_approver"

    def test_new_supplier_escalates(self, engine):
        ctx = _make_ctx(
            tool_name="register_supplier",
            classification="write",
        )
        result = engine.evaluate(ctx)
        assert result.decision == PolicyDecision.ESCALATE
        assert result.required_role == "security_admin"


class TestPolicyEngine_RuleTrace:
    """Verify that every evaluation produces a complete rule trace."""

    def test_rule_trace_non_empty(self, engine):
        ctx = _make_ctx()
        result = engine.evaluate(ctx)
        assert len(result.rule_trace) > 0

    def test_rule_trace_has_structure(self, engine):
        ctx = _make_ctx()
        result = engine.evaluate(ctx)
        for entry in result.rule_trace:
            assert "rule_id" in entry
            assert "matched" in entry


class TestPolicyEngine_RiskScoring:
    """Verify risk scoring is deterministic and uses integer arithmetic."""

    def test_read_only_low_risk(self, engine):
        ctx = _make_ctx(classification="read_only")
        result = engine.evaluate(ctx)
        assert result.risk_score <= 20

    def test_financial_high_risk(self, engine):
        ctx = _make_ctx(classification="financial", amount_minor=5_000_000)
        result = engine.evaluate(ctx)
        assert result.risk_score >= 60

    def test_suspended_max_risk(self, engine):
        ctx = _make_ctx(agent_status="suspended")
        result = engine.evaluate(ctx)
        assert result.risk_score == 100

    def test_risk_score_is_integer(self, engine):
        ctx = _make_ctx(classification="financial", injection_score=50)
        result = engine.evaluate(ctx)
        assert isinstance(result.risk_score, int)

    def test_risk_score_capped_at_100(self, engine):
        ctx = _make_ctx(
            classification="critical",
            amount_minor=100_000_000,
            injection_score=100,
        )
        result = engine.evaluate(ctx)
        assert result.risk_score <= 100


class TestPolicyEngine_ContentHash:
    """Verify policy content hashing for integrity."""

    def test_content_hash_deterministic(self, engine):
        h1 = engine.content_hash
        h2 = engine.content_hash
        assert h1 == h2

    def test_content_hash_is_sha256(self, engine):
        assert len(engine.content_hash) == 64
