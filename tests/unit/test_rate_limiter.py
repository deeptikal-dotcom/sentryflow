"""Tests for rate limiter — sliding window, isolation between keys."""
from __future__ import annotations

from backend.security.rate_limiter import RateLimiter, RateLimitConfig


class TestRateLimiter:
    def test_allows_under_limit(self):
        limiter = RateLimiter(RateLimitConfig(max_requests=5, window_seconds=60))
        allowed, remaining = limiter.check("agent-1")
        assert allowed
        assert remaining == 4

    def test_blocks_at_limit(self):
        limiter = RateLimiter(RateLimitConfig(max_requests=3, window_seconds=60))
        for _ in range(3):
            limiter.check("agent-1")
        allowed, remaining = limiter.check("agent-1")
        assert not allowed
        assert remaining == 0

    def test_different_keys_isolated(self):
        limiter = RateLimiter(RateLimitConfig(max_requests=2, window_seconds=60))
        limiter.check("agent-1")
        limiter.check("agent-1")
        allowed, _ = limiter.check("agent-1")
        assert not allowed

        allowed, remaining = limiter.check("agent-2")
        assert allowed
        assert remaining == 1

    def test_reset_clears_key(self):
        limiter = RateLimiter(RateLimitConfig(max_requests=2, window_seconds=60))
        limiter.check("agent-1")
        limiter.check("agent-1")
        limiter.reset("agent-1")
        allowed, _ = limiter.check("agent-1")
        assert allowed

    def test_remaining_decrements(self):
        limiter = RateLimiter(RateLimitConfig(max_requests=5, window_seconds=60))
        _, r1 = limiter.check("a")
        _, r2 = limiter.check("a")
        _, r3 = limiter.check("a")
        assert r1 == 4
        assert r2 == 3
        assert r3 == 2
