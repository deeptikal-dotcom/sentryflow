"""Deterministic policy engine — the authorization core of SentryFlow.

This engine evaluates tool calls against YAML-defined rules.
No LLM reasoning participates in authorization decisions.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


@dataclass
class PolicyResult:
    decision: PolicyDecision
    matched_rule_id: str | None = None
    rule_trace: list[dict] = field(default_factory=list)
    required_role: str | None = None
    reason: str | None = None
    risk_score: int = 0


@dataclass
class ToolCallContext:
    agent_id: str
    agent_status: str
    agent_capabilities: list[str]
    tool_name: str
    classification: str  # read_only|write|financial|critical
    parameters: dict[str, Any]
    amount_minor: int | None = None
    injection_score: int = 0
    session_id: str = ""


class PolicyEngine:
    def __init__(self, rules_yaml: str | None = None, rules_path: Path | None = None):
        if rules_yaml:
            self._policy = yaml.safe_load(rules_yaml)
        elif rules_path:
            self._policy = yaml.safe_load(rules_path.read_text())
        else:
            default_path = Path(__file__).parent.parent.parent / "data" / "policies" / "default.yaml"
            self._policy = yaml.safe_load(default_path.read_text())

        self._rules = sorted(
            self._policy.get("rules", []),
            key=lambda r: r.get("priority", 0),
            reverse=True,
        )
        self._thresholds = self._policy.get("thresholds", {})

    @property
    def version(self) -> int:
        return self._policy.get("version", 0)

    @property
    def name(self) -> str:
        return self._policy.get("name", "unknown")

    @property
    def content_hash(self) -> str:
        canonical = json.dumps(self._policy, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def evaluate(self, ctx: ToolCallContext) -> PolicyResult:
        trace = []

        for rule in self._rules:
            match_result = self._check_match(rule, ctx)
            trace_entry = {
                "rule_id": rule["id"],
                "matched": match_result,
                "priority": rule.get("priority", 0),
            }
            trace.append(trace_entry)

            if match_result:
                decision = PolicyDecision(rule["action"])
                return PolicyResult(
                    decision=decision,
                    matched_rule_id=rule["id"],
                    rule_trace=trace,
                    required_role=rule.get("required_role"),
                    reason=rule.get("reason"),
                    risk_score=self._compute_risk(ctx),
                )

        return PolicyResult(
            decision=PolicyDecision.DENY,
            matched_rule_id=None,
            rule_trace=trace,
            reason="No matching rule found — default deny",
            risk_score=self._compute_risk(ctx),
        )

    def _check_match(self, rule: dict, ctx: ToolCallContext) -> bool:
        match_spec = rule.get("match", {})

        if "classification" in match_spec:
            if ctx.classification != match_spec["classification"]:
                return False

        if "tool_name" in match_spec:
            if ctx.tool_name != match_spec["tool_name"]:
                return False

        if "agent_status" in match_spec:
            statuses = match_spec["agent_status"]
            if isinstance(statuses, list):
                if ctx.agent_status not in statuses:
                    return False
            elif ctx.agent_status != statuses:
                return False

        if "amount_minor_gte" in match_spec:
            if ctx.amount_minor is None or ctx.amount_minor < match_spec["amount_minor_gte"]:
                return False

        if "injection_score_gte" in match_spec:
            if ctx.injection_score < match_spec["injection_score_gte"]:
                return False

        conditions = rule.get("conditions", [])
        for cond in conditions:
            if "agent_has_capability" in cond:
                if cond["agent_has_capability"] and ctx.tool_name not in ctx.agent_capabilities:
                    return False

        return True

    def _compute_risk(self, ctx: ToolCallContext) -> int:
        score = 0

        classification_scores = {
            "read_only": 5,
            "write": 25,
            "financial": 60,
            "critical": 85,
        }
        score += classification_scores.get(ctx.classification, 50)

        if ctx.amount_minor is not None:
            if ctx.amount_minor >= 10_000_00:
                score += 20
            elif ctx.amount_minor >= 1_000_00:
                score += 10

        if ctx.injection_score > 0:
            score += min(ctx.injection_score // 2, 30)

        if ctx.agent_status in ("suspended", "revoked"):
            score = 100

        return min(score, 100)
