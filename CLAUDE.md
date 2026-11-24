# SentryFlow — CLAUDE.md

## Project Identity

- **Product:** SentryFlow
- **Category:** Agentic Transaction Security Platform
- **Tagline:** Autonomy without compromise.
- **Technical tagline:** Securing every agent. Verifying every action.
- **Repository:** sentryflow (private)
- **Primary color:** Midnight Navy #0B1424
- **Accent color:** Cyber Teal #2DD4BF

## Core Security Principle

An unauthorized business action must be prevented even when the underlying AI agent has been manipulated. The security gateway is deterministic and independent of LLM reasoning. Detection failure must never equal authorization.

## Architecture

Modular monolith with process-level container isolation:
- **Untrusted zone:** Agent containers (no access to DB, signing keys, payment systems)
- **Trusted zone:** Gateway container (policy engine, auth, audit) + Executor container (ERP/payment sim, signing keys)
- **Isolated zone:** Attack lab container (separate DB, credentials, no path to protected system)
- **Inference zone:** Ollama containers (dedicated per zone, no business data access)

Four Docker networks: `agent-net`, `trusted-net`, `lab-net`, `inference-net`.

## Technology Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, SQLite (WAL mode)
- **Frontend:** React 18, TypeScript, Vite, TailwindCSS, shadcn/ui, Recharts
- **LLM:** Ollama (Phi-4-mini or Llama 3.2 3B, CPU-only, sequential execution)
- **Crypto:** pyca/cryptography >= 48 (Ed25519 + ML-DSA-65 hybrid signatures, ML-KEM-768 demo, AES-256-GCM)
- **Testing:** pytest, Playwright
- **Deployment:** Docker Compose

## Permanent Rules

- All monetary amounts: integer minor-currency units (cents). Never floating-point for money.
- All timestamps: ISO 8601 UTC strings in the database.
- All IDs: UUID v4 as TEXT.
- Never store raw LLM reasoning in audit logs. Use structured decision summaries.
- Never log credentials, raw bank account numbers, or unnecessary PII.
- Bank-account identifiers use keyed HMAC-SHA256 fingerprints, not plain SHA-256.
- AES-GCM nonces must be unique per encryption operation (use os.urandom(12)).
- Approval nonces are single-use, cryptographically random.
- Canonical serialization for signed data: JSON with sorted keys, no whitespace, UTF-8.
- Hybrid signature verification requires BOTH Ed25519 AND ML-DSA-65 when hybrid mode is enabled. Never silently downgrade.
- Prompt-injection detection weights/thresholds are initial heuristics, not calibrated probabilities.
- Agents cannot approve their own actions or impersonate human identities.
- WebSocket auth uses short-lived single-use tickets, not long-lived JWTs.
- Container hardening: non-root, dropped capabilities, resource limits, read-only fs where practical.
- No paid APIs, cloud services, or commercial LLMs in the application.
- All dependencies must have commercially compatible licenses (MIT, Apache-2.0, BSD, PSF, ISC, HPND).
- Explicitly avoided: PyMuPDF (AGPL), Redis 7.4+ (RSALv2), any OpenAI/Anthropic/Gemini API.

## Commands

```bash
# Development
docker compose up                    # Start all services
docker compose up gateway executor   # Start trusted zone only
pytest tests/unit/ -v                # Run unit tests
pytest tests/security/ -v            # Run security invariant tests
pytest tests/integration/ -v         # Run integration tests

# Initial setup
python -m backend.cli init           # Create first admin user
python -m backend.cli generate-data  # Generate synthetic data
```

## File Conventions

- Backend code: `backend/` (Python, type-annotated)
- Frontend code: `frontend/src/` (TypeScript, strict mode)
- Policy rules: `data/policies/*.yaml`
- Attack scenarios: `attacks/scenarios/*.py`
- Tests mirror source structure: `tests/unit/test_<module>.py`
