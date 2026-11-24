# SentryFlow — Project Requirements

## Product Vision

SentryFlow is an Agentic Transaction Security Platform that protects AI procurement and financial agents from prompt injection, fraud, unauthorized actions, and manipulation.

**Core principle:** An unauthorized business action must be prevented even when the underlying AI agent has been manipulated.

## 16 Required Capabilities

| # | Capability | Description |
|---|-----------|-------------|
| R1 | Autonomous procurement agent simulation | Agents that negotiate, compare suppliers, process invoices via local LLM |
| R2 | Secure document processing | Parse and validate untrusted business documents (PDF, email, contracts) |
| R3 | Prompt injection defense | Multi-layer detection: regex, canary tokens, structural analysis, optional LLM classifier |
| R4 | Agent action security gateway | Deterministic policy engine intercepting all agent actions before execution |
| R5 | Agent identity & authorization | Capability-based access control with Ed25519 tokens |
| R6 | Tool-call interception | Every tool call passes through policy engine with allow/deny/escalate |
| R7 | Supplier & invoice fraud validation | Supplier registry, deduplication, bank-detail change detection, 3-way matching |
| R8 | Financial transaction risk assessment | Multi-factor risk scoring with integer arithmetic |
| R9 | Human-in-the-loop approval workflows | Nonce-bound, parameter-canonical approvals with replay protection |
| R10 | Multi-agent communication security | Signed inter-agent messages, delegation scope limits |
| R11 | Sensitive data protection | Field-level AES-256-GCM encryption, HMAC fingerprints, data classification |
| R12 | Tamper-evident audit trails | Hash-chained, signed checkpoints, sequence validation |
| R13 | Post-quantum cryptographic readiness | ML-DSA-65 + Ed25519 hybrid signatures via pyca/cryptography |
| R14 | Enterprise security dashboard | React dashboard with real-time WebSocket updates |
| R15 | Attack simulation laboratory | Isolated environment with 10+ attack scenarios and benchmarking |
| R16 | Automated testing & deployment | pytest, Playwright, Docker Compose, CI/CD |

## Zero-Cost Requirements

- No paid APIs, cloud services, or commercial LLMs
- Local models via Ollama (Phi-4-mini or Llama 3.2 3B)
- All dependencies commercially licensed (MIT, Apache-2.0, BSD)
- Offline-capable after initial setup

## Security Invariants

| ID | Invariant |
|----|-----------|
| SI-1 | Untrusted documents cannot grant permissions |
| SI-2 | Agents cannot bypass the security gateway |
| SI-3 | Agent-generated claims cannot serve as authorization |
| SI-4 | Financial actions fail closed on auth failure |
| SI-5 | Approval binds exact transaction parameters |
| SI-6 | Modified/replayed approvals are rejected |
| SI-7 | High-risk actions require independent human authorization |
| SI-8 | Decisions and evidence are auditable with tamper detection |
