"""Base agent class for SentryFlow procurement agents.

Agents run in the untrusted zone and communicate with the gateway
via HTTP only. They have no direct access to the database, signing keys,
or payment systems. All tool calls go through the security gateway.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime

logger = logging.getLogger("sentryflow.agent")


@dataclass
class ToolCall:
    tool_name: str
    parameters: dict
    context: str | None = None


@dataclass
class ToolCallResult:
    tool_call_id: str
    decision: str  # allow|deny|escalate
    risk_score: int
    approval_required: bool
    approval_id: str | None = None
    required_role: str | None = None
    reason: str | None = None
    execution_result: dict | None = None


@dataclass
class AgentState:
    agent_id: str
    agent_type: str
    capabilities: list[str]
    session_id: str
    tool_calls_made: int = 0
    tool_calls_denied: int = 0
    tool_calls_escalated: int = 0
    created_at: str = ""


class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: list[str],
        gateway_url: str = "http://gateway:8000",
    ):
        self.state = AgentState(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            session_id=f"session-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            created_at=datetime.now(UTC).isoformat(),
        )
        self._gateway_url = gateway_url.rstrip("/")
        self._ollama_client = None

    @abstractmethod
    async def process_task(self, task: dict) -> dict:
        """Process a domain-specific task. Subclasses implement this."""

    async def call_tool(self, tool: ToolCall) -> ToolCallResult:
        self.state.tool_calls_made += 1
        logger.info(
            f"Agent {self.state.agent_id} calling tool: {tool.tool_name}"
        )

        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "agent_id": self.state.agent_id,
                "tool_name": tool.tool_name,
                "parameters": tool.parameters,
            }
            if tool.context:
                payload["context"] = tool.context

            resp = await client.post(
                f"{self._gateway_url}/api/v1/gateway/evaluate",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        result = ToolCallResult(
            tool_call_id=data.get("tool_call_id", ""),
            decision=data.get("decision", "deny"),
            risk_score=data.get("risk_score", 0),
            approval_required=data.get("approval_required", False),
            approval_id=data.get("approval_id"),
            required_role=data.get("required_role"),
            reason=data.get("reason"),
        )

        if result.decision == "deny":
            self.state.tool_calls_denied += 1
            logger.warning(f"Tool call denied: {result.reason}")
        elif result.decision == "escalate":
            self.state.tool_calls_escalated += 1
            logger.info(f"Tool call escalated, approval required: {result.required_role}")

        return result

    def get_status(self) -> dict:
        return {
            "agent_id": self.state.agent_id,
            "agent_type": self.state.agent_type,
            "session_id": self.state.session_id,
            "tool_calls_made": self.state.tool_calls_made,
            "tool_calls_denied": self.state.tool_calls_denied,
            "tool_calls_escalated": self.state.tool_calls_escalated,
        }
