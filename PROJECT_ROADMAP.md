# SentryFlow — Project Roadmap

## Phase 1: Foundation

### 1A: Scaffolding & Infrastructure
- [x] Directory structure
- [x] CLAUDE.md
- [x] pyproject.toml with pinned dependencies
- [x] Docker Compose with 4-network isolation
- [x] Container hardening (non-root, dropped caps, resource limits)
- [x] Database models (complete schema)
- [x] FastAPI app skeleton with route stubs
- [x] .gitignore, .env.example
- [ ] Verify Docker containers start
- [ ] Verify network isolation

### 1B: Authentication & Core API
- [x] Auth module (argon2, JWT, WebSocket tickets)
- [x] Role-based access control (6 roles)
- [x] sentryflow-init CLI
- [x] Protected endpoints with role checks
- [x] Auth tests passing

### 1C: Domain Model & Synthetic Data
- [x] Synthetic data generator
- [x] ERP simulator
- [x] Payment system simulator
- [x] 3-way matching engine
- [x] Integer currency tests

### 1D: Ollama & PQC Verification
- [ ] Install Ollama
- [ ] Benchmark local model
- [ ] Verify ML-DSA/ML-KEM in Python 3.11+ container
- [ ] Deterministic test fixtures

## Phase 2: Security Gateway

- [x] 2A: Policy engine, tool interception, risk scoring
- [x] 2B: Prompt injection detection (4 layers)
- [x] 2C: Approval workflows with replay protection
- [x] 2D: Agent framework (5 agents)
- [x] 2E: Trusted Executor (business action execution)
- [x] 2F: End-to-end pipeline (gateway → policy → approval → executor → audit)
- [x] 2G: Integration tests (11 tests covering full pipeline)

## Phase 3: Trust, Audit & Crypto
- [x] 3A: Ed25519 signatures, hybrid PQC, key management
- [x] 3B: Hash-chain audit log, verification
- [ ] 3B+: Audit checkpoints at configurable intervals
- [ ] 3C: ML-DSA-65 signed execution receipts
- [x] 3D: Field encryption (AES-256-GCM), HMAC fingerprints

## Phase 4: Dashboard, Lab & Polish
- [x] 4A: Dashboard core (React + shadcn/ui)
- [x] 4B: Extended dashboard pages (Agents, Approvals, Suppliers, Audit, Threats)
- [x] 4C: Attack simulation lab (10 scenarios, isolated)
- [ ] 4C+: Integrate attack lab with real gateway pipeline
- [ ] 4D: Frontend agent task submission UI
- [ ] 4E: WebSocket live feed on dashboard
- [ ] 4F: Testing, docs, deployment verification
