"""Ollama HTTP client wrapper for SentryFlow.

Provides structured interaction with local Ollama instance.
Supports sequential execution (one request at a time).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from backend.config import settings

logger = logging.getLogger("sentryflow.ollama")


@dataclass
class OllamaResponse:
    text: str
    model: str
    total_duration_ms: int
    prompt_eval_count: int
    eval_count: int
    tokens_per_second: float


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.ollama_model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> OllamaResponse:
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system:
            payload["system"] = system

        start = time.monotonic()
        resp = await self._client.post(f"{self._base_url}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        elapsed_ms = int((time.monotonic() - start) * 1000)

        eval_count = data.get("eval_count", 0)
        total_ns = data.get("total_duration", 0)
        tps = (eval_count / (total_ns / 1e9)) if total_ns > 0 else 0

        return OllamaResponse(
            text=data.get("response", ""),
            model=data.get("model", self._model),
            total_duration_ms=elapsed_ms,
            prompt_eval_count=data.get("prompt_eval_count", 0),
            eval_count=eval_count,
            tokens_per_second=round(tps, 2),
        )

    async def check_health(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[dict]:
        try:
            resp = await self._client.get(f"{self._base_url}/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])
        except Exception:
            return []

    async def close(self):
        await self._client.aclose()
