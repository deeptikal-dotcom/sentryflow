"""Agent runner — LLM-driven autonomous procurement agent.

Runs inside the untrusted agent container. Communicates with:
- Ollama (for reasoning and tool-call generation)
- Gateway (for all business actions, via HTTP)

Has NO access to: database, signing keys, payment systems, audit log.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass

from backend.agents.ollama_client import OllamaClient, OllamaResponse
from backend.agents.procurement_agents import AGENT_REGISTRY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("sentryflow.agent_runner")

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway:8000")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama-agent:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi4-mini:latest")

SYSTEM_PROMPT = """You are a procurement agent. You process business tasks by calling tools.
You MUST respond with a JSON object containing exactly one tool call:
{"tool_name": "<tool>", "parameters": {<params>}, "reasoning": "<brief explanation>"}

Available tools:
- read_supplier: {"supplier_id": "..."}
- create_po: {"supplier_id": "...", "items": [...], "total_amount_minor": N, "currency": "USD"}
- process_invoice: {"document_id": "...", "invoice_text": "..."}
- create_payment: {"invoice_id": "...", "supplier_id": "...", "amount_minor": N, "currency": "USD", "bank_account_id": "..."}
- list_suppliers: {}

Respond ONLY with the JSON object. No other text."""


@dataclass
class AgentTask:
    task_id: str
    agent_type: str
    agent_id: str
    description: str
    parameters: dict


@dataclass
class AgentRunResult:
    task_id: str
    agent_id: str
    success: bool
    tool_calls_made: int
    gateway_decisions: list[dict]
    llm_used: bool
    model: str | None
    total_latency_ms: int
    error: str | None = None


def parse_tool_call(text: str) -> dict | None:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


async def run_task_with_llm(
    ollama: OllamaClient,
    task: AgentTask,
    gateway_url: str,
) -> AgentRunResult:
    """Execute a task using LLM reasoning to generate tool calls."""
    import time

    import httpx

    start = time.monotonic()
    gateway_decisions: list[dict] = []
    model_name: str | None = None
    llm_used = False

    prompt = (
        f"Task: {task.description}\n"
        f"Agent type: {task.agent_type}\n"
        f"Parameters: {json.dumps(task.parameters)}\n\n"
        "Generate the appropriate tool call."
    )

    try:
        response: OllamaResponse = await ollama.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=512,
        )
        llm_used = True
        model_name = response.model
        logger.info(
            f"LLM response ({response.eval_count} tokens, "
            f"{response.tokens_per_second} tok/s): {response.text[:200]}"
        )

        tool_call = parse_tool_call(response.text)
        if not tool_call or "tool_name" not in tool_call:
            return AgentRunResult(
                task_id=task.task_id,
                agent_id=task.agent_id,
                success=False,
                tool_calls_made=0,
                gateway_decisions=gateway_decisions,
                llm_used=llm_used,
                model=model_name,
                total_latency_ms=int((time.monotonic() - start) * 1000),
                error=f"LLM did not produce valid tool call: {response.text[:200]}",
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "agent_id": task.agent_id,
                "tool_name": tool_call["tool_name"],
                "parameters": tool_call.get("parameters", {}),
                "auto_execute": True,
            }
            if "context" in tool_call:
                payload["context"] = str(tool_call["context"])

            resp = await client.post(
                f"{gateway_url}/api/v1/gateway/evaluate",
                json=payload,
            )
            resp.raise_for_status()
            decision = resp.json()
            gateway_decisions.append(decision)
            logger.info(
                f"Gateway decision: {decision.get('decision')} "
                f"(risk={decision.get('risk_score')})"
            )

        elapsed = int((time.monotonic() - start) * 1000)
        return AgentRunResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            success=True,
            tool_calls_made=1,
            gateway_decisions=gateway_decisions,
            llm_used=llm_used,
            model=model_name,
            total_latency_ms=elapsed,
        )

    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        logger.error(f"Task failed: {e}")
        return AgentRunResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            success=False,
            tool_calls_made=len(gateway_decisions),
            gateway_decisions=gateway_decisions,
            llm_used=llm_used,
            model=model_name,
            total_latency_ms=elapsed,
            error=str(e),
        )


async def run_task_deterministic(
    task: AgentTask,
    gateway_url: str,
) -> AgentRunResult:
    """Fallback: execute task without LLM using the structured agent classes."""
    import time

    start = time.monotonic()
    gateway_decisions: list[dict] = []

    agent_cls = AGENT_REGISTRY.get(task.agent_type)
    if not agent_cls:
        return AgentRunResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            success=False,
            tool_calls_made=0,
            gateway_decisions=[],
            llm_used=False,
            model=None,
            total_latency_ms=int((time.monotonic() - start) * 1000),
            error=f"Unknown agent type: {task.agent_type}",
        )

    agent = agent_cls(agent_id=task.agent_id, gateway_url=gateway_url)
    try:
        result = await agent.process_task(task.parameters)
        elapsed = int((time.monotonic() - start) * 1000)
        return AgentRunResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            success=result.get("status") != "failed",
            tool_calls_made=agent.state.tool_calls_made,
            gateway_decisions=[result],
            llm_used=False,
            model=None,
            total_latency_ms=elapsed,
        )
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        return AgentRunResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            success=False,
            tool_calls_made=agent.state.tool_calls_made,
            gateway_decisions=[],
            llm_used=False,
            model=None,
            total_latency_ms=elapsed,
            error=str(e),
        )


async def process_task(task: AgentTask, gateway_url: str) -> AgentRunResult:
    """Try LLM-driven execution first, fall back to deterministic."""
    ollama = OllamaClient(base_url=OLLAMA_URL, model=OLLAMA_MODEL)
    try:
        healthy = await ollama.check_health()
        if healthy:
            logger.info(f"Ollama available — using LLM for task {task.task_id}")
            return await run_task_with_llm(ollama, task, gateway_url)
        else:
            logger.warning("Ollama unavailable — using deterministic agent")
            return await run_task_deterministic(task, gateway_url)
    finally:
        await ollama.close()


async def main():
    logger.info("SentryFlow Agent Runner starting")
    logger.info(f"Gateway: {GATEWAY_URL}")
    logger.info(f"Ollama: {OLLAMA_URL} (model: {OLLAMA_MODEL})")

    ollama = OllamaClient(base_url=OLLAMA_URL, model=OLLAMA_MODEL)
    healthy = await ollama.check_health()
    await ollama.close()

    if healthy:
        models = await OllamaClient(base_url=OLLAMA_URL).list_models()
        logger.info(f"Ollama healthy, models: {[m.get('name') for m in models]}")
    else:
        logger.warning("Ollama not reachable — agent will use deterministic mode")

    logger.info("Agent runner ready. Waiting for tasks...")

    while True:
        await asyncio.sleep(60)
        logger.debug("Agent runner heartbeat")


if __name__ == "__main__":
    asyncio.run(main())
