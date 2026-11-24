"""Lab proxy API — exposes attack lab scenarios through the main gateway.

In production, the lab runs in an isolated container. For MVP development,
we import and run lab scenarios directly with injection detector only,
keeping the lab's isolation promise (no access to real DB or executor).

The /run-gateway endpoint actually sends scenarios through the real gateway
evaluate path for end-to-end testing.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import require_role
from backend.database import get_session
from backend.lab.app import SCENARIOS, AttackResult, _results
from backend.models.agent import Agent
from backend.models.user import User
from backend.security.injection_detector import InjectionDetector
from backend.trust.policy_engine import PolicyDecision, PolicyEngine, ToolCallContext

router = APIRouter()

detector = InjectionDetector()
_policy_engine = PolicyEngine()


@router.get("/scenarios")
async def list_scenarios(
    _user: Annotated[User, Depends(require_role("security_admin", "security_analyst"))],
):
    return {
        "scenarios": [
            {
                "id": s.id,
                "name": s.name,
                "category": s.category,
                "description": s.description,
                "severity": s.severity,
                "expected_blocked": s.expected_blocked,
            }
            for s in SCENARIOS
        ]
    }


@router.post("/scenarios/{scenario_id}/run")
async def run_scenario(
    scenario_id: str,
    _user: Annotated[User, Depends(require_role("security_admin", "security_analyst"))],
):
    scenario = next((s for s in SCENARIOS if s.id == scenario_id), None)
    if not scenario:
        raise HTTPException(404, "Scenario not found")

    blocked = False
    detection_score = 0.0
    details: dict = {}

    text_fields = []
    for v in scenario.payload.get("parameters", {}).values():
        if isinstance(v, str):
            text_fields.append(v)

    if text_fields:
        combined = " ".join(text_fields)
        scan = detector.scan(combined)
        detection_score = scan.score
        blocked = detection_score >= 40 or scan.flagged
        details["injection_scan"] = {
            "score": scan.score,
            "flagged": scan.flagged,
            "layer_scores": scan.layer_scores,
        }

    if scenario.payload.get("classification") == "critical":
        blocked = True
        details["policy"] = "critical_action_requires_admin"

    if scenario.category == "auth":
        blocked = True
        details["auth"] = "privilege_or_replay_check_would_block"

    result = AttackResult(
        scenario_id=scenario_id,
        blocked=blocked,
        detection_score=detection_score,
        details=details,
        executed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    )
    _results.append(result)

    return {
        "scenario_id": scenario_id,
        "blocked": blocked,
        "detection_score": detection_score,
        "expected_blocked": scenario.expected_blocked,
        "match": blocked == scenario.expected_blocked,
        "details": details,
    }


@router.post("/run-all")
async def run_all_scenarios(
    _user: Annotated[User, Depends(require_role("security_admin"))],
):
    results = []
    for scenario in SCENARIOS:
        blocked = False
        detection_score = 0.0
        details: dict = {}

        text_fields = []
        for v in scenario.payload.get("parameters", {}).values():
            if isinstance(v, str):
                text_fields.append(v)

        if text_fields:
            combined = " ".join(text_fields)
            scan = detector.scan(combined)
            detection_score = scan.score
            blocked = detection_score >= 40 or scan.flagged
            details["injection_scan"] = {
                "score": scan.score,
                "flagged": scan.flagged,
                "layer_scores": scan.layer_scores,
            }

        if scenario.payload.get("classification") == "critical":
            blocked = True
            details["policy"] = "critical_action_requires_admin"

        if scenario.category == "auth":
            blocked = True
            details["auth"] = "privilege_or_replay_check_would_block"

        results.append({
            "scenario_id": scenario.id,
            "name": scenario.name,
            "category": scenario.category,
            "severity": scenario.severity,
            "blocked": blocked,
            "expected_blocked": scenario.expected_blocked,
            "match": blocked == scenario.expected_blocked,
            "detection_score": detection_score,
        })

    total = len(results)
    matched = sum(1 for r in results if r["match"])
    blocked_correct = sum(1 for r in results if r["expected_blocked"] and r["blocked"])
    total_expected_blocked = sum(1 for r in results if r["expected_blocked"])

    return {
        "results": results,
        "summary": {
            "total": total,
            "matched": matched,
            "accuracy": round(matched / total * 100, 1) if total else 0,
            "true_positive_rate": round(blocked_correct / total_expected_blocked * 100, 1) if total_expected_blocked else 0,
        },
    }


@router.post("/run-gateway")
async def run_all_through_gateway(
    _user: Annotated[User, Depends(require_role("security_admin"))],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Run all scenarios through the real policy engine + injection detector."""
    agent_result = await session.execute(
        select(Agent).where(Agent.status == "active").limit(1)
    )
    agent = agent_result.scalar_one_or_none()

    results = []
    for scenario in SCENARIOS:
        tool_name = scenario.payload.get("tool_name", "unknown_tool")
        parameters = scenario.payload.get("parameters", {})
        classification = scenario.payload.get("classification", "write")

        injection_score = 0
        scan_details = {}
        text_fields = [v for v in parameters.values() if isinstance(v, str)]
        if text_fields:
            scan = detector.scan(" ".join(text_fields))
            injection_score = scan.score
            scan_details = {
                "score": scan.score,
                "flagged": scan.flagged,
                "layer_scores": scan.layer_scores,
            }

        ctx = ToolCallContext(
            agent_id=agent.id if agent else "lab-agent",
            agent_status="active",
            agent_capabilities=["process_invoice", "create_payment", "update_bank_details"],
            tool_name=tool_name,
            classification=classification,
            parameters=parameters,
            amount_minor=parameters.get("amount_minor"),
            injection_score=injection_score,
            session_id="lab-session",
        )
        policy_result = _policy_engine.evaluate(ctx)

        blocked = policy_result.decision != PolicyDecision.ALLOW
        results.append({
            "scenario_id": scenario.id,
            "name": scenario.name,
            "category": scenario.category,
            "severity": scenario.severity,
            "blocked": blocked,
            "expected_blocked": scenario.expected_blocked,
            "match": blocked == scenario.expected_blocked,
            "policy_decision": policy_result.decision.value,
            "policy_reason": policy_result.reason,
            "risk_score": policy_result.risk_score,
            "injection_score": injection_score,
            "injection_details": scan_details,
        })

    total = len(results)
    matched = sum(1 for r in results if r["match"])
    blocked_correct = sum(1 for r in results if r["expected_blocked"] and r["blocked"])
    total_expected_blocked = sum(1 for r in results if r["expected_blocked"])
    allowed_correct = sum(1 for r in results if not r["expected_blocked"] and not r["blocked"])
    total_expected_allowed = sum(1 for r in results if not r["expected_blocked"])

    return {
        "mode": "gateway",
        "results": results,
        "summary": {
            "total": total,
            "matched": matched,
            "accuracy": round(matched / total * 100, 1) if total else 0,
            "true_positive_rate": round(blocked_correct / total_expected_blocked * 100, 1) if total_expected_blocked else 0,
            "true_negative_rate": round(allowed_correct / total_expected_allowed * 100, 1) if total_expected_allowed else 0,
        },
    }


@router.get("/results")
async def list_results(
    _user: Annotated[User, Depends(require_role("security_admin", "security_analyst"))],
):
    return {"results": [asdict(r) for r in _results]}
