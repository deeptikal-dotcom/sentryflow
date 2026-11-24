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
- [ ] Protected endpoints with role checks
- [ ] Auth tests passing

### 1C: Domain Model & Synthetic Data
- [ ] Synthetic data generator
- [ ] ERP simulator
- [ ] Payment system simulator
- [ ] 3-way matching engine
- [ ] Integer currency tests

### 1D: Ollama & PQC Verification
- [ ] Install Ollama
- [ ] Benchmark local model
- [ ] Verify ML-DSA/ML-KEM in Python 3.11+ container
- [ ] Deterministic test fixtures

## Phase 2: Security Gateway
- [ ] 2A: Policy engine, tool interception, risk scoring
- [ ] 2B: Prompt injection detection (4 layers)
- [ ] 2C: Approval workflows with replay protection
- [ ] 2D: Agent framework (5 agents)

## Phase 3: Trust, Audit & Crypto
- [ ] 3A: Hybrid signatures, PQC, key management
- [ ] 3B: Hash-chain audit log, checkpoints
- [ ] 3C: Supplier/invoice validation, 3-way matching
- [ ] 3D: Field encryption, data classification

## Phase 4: Dashboard, Lab & Polish
- [ ] 4A: Dashboard core (React + shadcn/ui)
- [ ] 4B: Extended dashboard pages
- [ ] 4C: Attack simulation lab (isolated)
- [ ] 4D: Testing, docs, deployment
