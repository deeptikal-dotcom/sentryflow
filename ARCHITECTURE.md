# SentryFlow — Architecture

## Trust Boundaries

### Untrusted Zone (agent-net)
- Agent containers with 5 procurement agent types
- Document parsing (untrusted input)
- Ollama LLM for agent inference
- **No access to:** database, signing keys, payment systems, audit log

### Trusted Zone (trusted-net)
- **Gateway container:** policy engine, injection detection, approval router, auth/RBAC, audit logger
- **Executor container:** ERP simulator, payment simulator, signing keys, database writes
- **Frontend container:** React dashboard served via nginx reverse proxy

### Isolated Zone (lab-net)
- Attack lab container with separate SQLite database
- Own credentials, no shared state with protected system
- 10 attack scenarios for security evaluation

### Inference Zone (inference-net)
- Ollama containers dedicated per zone
- No business data access

## Component Responsibilities

### Policy Engine (`backend/trust/policy_engine.py`)
- Loads YAML rules sorted by priority (highest first)
- Evaluates match conditions: classification, tool_name, agent_status, capabilities
- Risk scoring: classification base + amount bonus + injection bonus, capped at 100
- **Default-deny:** no matching rule = DENY with reason
- **Deterministic:** no LLM involvement in authorization decisions

### Injection Detector (`backend/security/injection_detector.py`)
- Layer 1: 20 regex patterns across 8 categories (weight: 0.30)
- Layer 2: Canary token injection/verification (weight: 0.30)
- Layer 3: Structural boundary analysis — delimiter escapes, chat format tokens (weight: 0.20)
- Layer 4: Optional LLM classifier (weight: 0.20, disabled by default)
- Combined score >= 50 flags as injection
- **Not an authorization guarantee** — supplementary detection only

### Approval Manager (`backend/trust/approval_manager.py`)
- Creates nonce-bound approval requests with canonical parameter hashing
- Validates: role, not self-approving, not expired, not already resolved
- Single-use consumption: marks consumed atomically
- Parameter hash verification before execution

### Audit Logger (`backend/audit/audit_logger.py`)
- Append-only: no UPDATE/DELETE API
- Hash chain: each record links to previous via SHA-256
- Sequence gap detection: monotonic sequence numbers
- Signed checkpoints every N records
- Structured decision summaries (never raw LLM reasoning)

### Document Processor (`backend/security/document_processor.py`)
- File size limits (10 MB), page count limits (100)
- File signature (magic bytes) validation
- Text extraction: pypdf (PDF), pytesseract (OCR), stdlib (CSV/JSON/text)
- Injection scanning of all extracted text
- Quarantine threshold: score >= 40

## Data Flow

```
Agent Request → Gateway Auth → Injection Scan → Policy Engine → Decision
                                                      │
                                              ┌───────┴──────────┐
                                              │                  │
                                           ALLOW             ESCALATE
                                              │                  │
                                        Execute via          Create Approval
                                        Executor           → Human Reviews
                                              │                  │
                                        Audit Log          Approve/Deny
                                                                 │
                                                           Revalidate
                                                                 │
                                                        Execute + Consume
                                                                 │
                                                           Audit Log
```

## Database

- SQLite in WAL mode (concurrent reads, serialized writes)
- 20+ tables covering: users, agents, suppliers, POs, invoices, goods receipts, payments, documents, tool calls, approvals, incidents, audit log, policy versions
- All monetary amounts: integer minor-currency units (cents)
- All timestamps: ISO 8601 UTC strings
- All IDs: UUID v4 as TEXT

## Network Isolation (Docker Compose)

```
agent-net:    agent ↔ gateway, agent ↔ ollama-agent
trusted-net:  gateway ↔ executor, gateway ↔ frontend, gateway ↔ ollama-trusted
lab-net:      lab ↔ ollama-lab (no path to trusted-net)
inference-net: ollama containers
```

## Container Hardening

All containers enforce: `security_opt: no-new-privileges`, `cap_drop: ALL`, `mem_limit`, `cpus`, `read_only` where practical. Non-root user in all custom images.
