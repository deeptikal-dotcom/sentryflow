# SentryFlow — Known Limitations

## Security Scope

1. **100% block rate applies to 10 evaluated scenarios only.** This does not constitute universal prompt-injection protection or guaranteed security against all attack vectors. Novel attack patterns not represented in the current scenario set may not be detected.

2. **Injection detection recall: 26.7%** (regex-only without LLM classifier). The system relies on authorization independence — detection supplements but does not replace the deterministic policy engine. A missed injection does not equal a successful attack.

3. **Policy rules are initial heuristics.** Thresholds, risk scores, and weights have not been calibrated on production traffic. They require tuning for each deployment environment.

## Infrastructure

4. **SQLite for production** — Appropriate for MVP single-instance deployments. Migration to PostgreSQL is straightforward via SQLAlchemy but not implemented. WAL mode supports concurrent reads but writes are serialized.

5. **Python 3.11 required for `pip install`** — pydantic-core lacks pre-built wheels for Python 3.15. CI and Docker use Python 3.11. Local development requires Python 3.11.

6. **CPU-only LLM inference** — Llama 3.2 3B runs at 17.7 tokens/sec on Intel i5. Latency ranges from 920ms to 4,728ms per agent task. Faster on Apple Silicon or GPU, but no GPU configuration is provided.

7. **Frontend runs as root in nginx container** — Required for nginx cache directory management. Mitigated by `cap_drop: ALL`, read-only filesystem, and `no-new-privileges`.

## Operational

8. **No horizontal scaling** — Single-instance design. No load balancing, session affinity, or distributed state management.

9. **No key rotation automation** — Signing keys and encryption keys must be rotated manually. Key manager supports rotation but no scheduled automation exists.

10. **No real payment gateway integration** — The executor simulates ERP and payment operations. Integration with actual financial systems requires additional development.

11. **WebSocket reconnection** — The frontend does not implement automatic WebSocket reconnection on connection loss. Manual page refresh is required.

## Testing

12. **Integration tests require running services** — The integration test suite requires the backend server to be running. CI runs these tests but they may be skipped if unit tests fail first.

13. **No end-to-end Playwright test suite in CI** — Browser verification was performed manually with Playwright. An automated Playwright CI pipeline is not configured.
