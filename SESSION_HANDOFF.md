# SentryFlow — Session Handoff

## Last Session: 2026-11-23

### What Was Done
- Full project scaffolding for SentryFlow agentic transaction security platform
- Architecture approved after two review cycles with 16 mandatory corrections incorporated
- Complete database schema implemented (20+ tables with integer currency, 3-way matching, HMAC fingerprints)
- Authentication system with argon2 password hashing, JWT tokens, WebSocket tickets, 6 RBAC roles
- Docker Compose with 4-network isolation (trusted-net, agent-net, inference-net, lab-net)
- Container hardening (non-root, dropped capabilities, resource limits, read-only fs)

### Current State
- Phase 1A in progress
- Dependencies installing
- Tests not yet run

### Exact Next Steps
1. Verify all tests pass
2. Verify Docker containers start with network isolation
3. Install Ollama and benchmark a model
4. Verify PQC (ML-DSA/ML-KEM) availability
5. Create initial commit and push to private GitHub repo `sentryflow`
6. Begin Phase 1C: synthetic data generator and simulated systems
7. Begin Phase 2: security gateway (policy engine, injection detection)

### Key Decisions Made
- Product name: SentryFlow
- PQC library: pyca/cryptography >= 48 (not liboqs)
- Architecture: Modular monolith with process-level container isolation
- LLM: Ollama with Phi-4-mini or Llama 3.2 3B (CPU-only, sequential execution)
- Database: SQLite with WAL mode (all money as integer minor-currency units)
- Gateway owns all authorization and audit; Executor owns business data writes
- WebSocket auth via short-lived single-use tickets (not long-lived JWTs)
- Bank account identifiers use HMAC-SHA256 (not plain SHA-256)

### Files Modified
- All files are new (greenfield project)
