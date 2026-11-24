"""Simple in-memory rate limiter for the security gateway.

Uses sliding window counters. No external dependencies (no Redis).
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    max_requests: int = 60
    window_seconds: int = 60


class RateLimiter:
    def __init__(self, config: RateLimitConfig | None = None):
        self._config = config or RateLimitConfig()
        self._windows: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self._config.window_seconds

        timestamps = self._windows[key]
        timestamps[:] = [t for t in timestamps if t > cutoff]

        remaining = self._config.max_requests - len(timestamps)

        if remaining <= 0:
            return False, 0

        timestamps.append(now)
        return True, remaining - 1

    def reset(self, key: str) -> None:
        self._windows.pop(key, None)

    def reset_all(self) -> None:
        self._windows.clear()
