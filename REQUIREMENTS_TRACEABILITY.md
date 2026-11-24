# SentryFlow — Requirements Traceability Matrix

## Capabilities (R1–R16)

| ID | Requirement | Status | Implementation | Tests |
|----|------------|--------|----------------|-------|
| R1 | Security gateway intercepts all agent tool calls | ✅ Done | `backend/api/gateway.py` — POST /evaluate endpoint | `test_pipeline.py`, `test_invariants.py` |
| R2 | Secure document processing (PDF, text, image OCR) | ✅ Done | `backend/security/document_processor.py` — pypdf extraction, OCR, injection scan | `test_documents.py` (23 tests) |
| R3 | Deterministic policy engine (no LLM in auth path) | ✅ Done | `backend/trust/policy_engine.py` — YAML rules, priority-ordered | `test_invariants.py`, `test_policy.py` |
| R4 | 4-layer prompt injection detection | ✅ Done | `backend/security/injection_detector.py` — regex, canary, structural, LLM classifier | `test_injection.py` |
| R5 | Human approval workflows with parameter binding | ✅ Done | `backend/trust/approval_manager.py` — nonce-bound, canonical hash, single-use | `test_pipeline.py::TestApprovalFlow` |
| R6 | Replay-protected approval consumption | ✅ Done | Approval consumed flag + canonical hash verification | `test_pipeline.py::TestReplayProtection` |
| R7 | Hash-chained tamper-evident audit log | ✅ Done | `backend/audit/audit_logger.py` — SHA-256 chain, genesis hash | `test_audit.py` |
| R8 | Role-based access control (6 roles) | ✅ Done | `backend/api/auth.py` — require_role dependency | `test_auth.py`, `test_executor_security.py` |
| R9 | Agent capability enforcement | ✅ Done | Policy engine checks agent_capabilities | `test_invariants.py::TestSI2` |
| R10 | Multi-agent communication security | ⚠️ Partial | Agent framework with 5 types, gateway interception | Agents registered and evaluated through gateway |
| R11 | ERP/Payment simulation with 3-way matching | ✅ Done | `backend/simulation/erp_simulator.py`, `payment_simulator.py` | `test_erp.py`, `test_payment.py` |
| R12 | Audit checkpoints with signed export | ✅ Done | `backend/audit/audit_logger.py` — checkpoints with Ed25519 + ML-DSA signatures | `test_audit.py::TestAuditCheckpoints` |
| R13 | Post-quantum cryptography (ML-DSA-65, ML-KEM-768) | ✅ Done | `backend/trust/crypto.py`, `key_manager.py` — hybrid signatures, KEM demo | `test_crypto.py` (28 tests) |
| R14 | Real-time dashboard with WebSocket feed | ✅ Done | `frontend/src/pages/Dashboard.tsx`, `ActivityFeed.tsx`, `useWebSocket.ts` | Frontend build passes, TypeScript strict |
| R15 | Attack simulation lab integrated with gateway | ✅ Done | `backend/api/lab_proxy.py` — 10 scenarios, gateway pipeline integration | `test_attack_lab.py` |
| R16 | Trusted execution with signed receipts | ✅ Done | `backend/executor/executor.py` — hybrid PQC-signed receipts | `test_pipeline.py`, `test_executor_security.py` |

## Security Invariants (SI-1–SI-8)

| ID | Invariant | Status | Verification |
|----|-----------|--------|-------------|
| SI-1 | Untrusted documents cannot grant permissions | ✅ | `test_invariants.py::TestSI1` — injection scores never auto-allow |
| SI-2 | Agents cannot bypass the security gateway | ✅ | `test_invariants.py::TestSI2` — suspended agents denied, capability enforcement |
| SI-3 | Agent-generated claims cannot serve as authorization | ✅ | `test_invariants.py::TestSI3` — financial always requires human, critical requires admin |
| SI-4 | Financial actions fail closed on auth failure | ✅ | `test_invariants.py::TestSI4` — financial never auto-allowed, default deny |
| SI-5 | Changed parameters invalidate approvals | ✅ | `test_executor_security.py::TestApprovalParameterBinding` — tampered amount rejected |
| SI-6 | Approval consumption is single-use | ✅ | `test_pipeline.py::TestReplayProtection`, `test_concurrency.py` — double-execute blocked |
| SI-7 | High-risk actions require human authorization | ✅ | `test_invariants.py::TestSI7`, `test_executor_security.py::TestAutoExecuteCannotBypassEscalation` |
| SI-8 | Decisions and evidence are auditable with tamper detection | ✅ | `test_audit.py` — chain verification, tamper detection, checkpoints |

## Additional Security Guarantees (Executor Hardening)

| Guarantee | Status | Test |
|-----------|--------|------|
| Only authorized human roles can trigger execution | ✅ | `test_executor_security.py::TestExecutorRoleEnforcement` |
| Fabricated tool_call_id rejected | ✅ | `test_executor_security.py::TestExecutorRequiresGatewayAuthorization` |
| Suspended agent blocked at execution time | ✅ | `test_executor_security.py::TestSuspendedAgentAtExecutionTime` |
| auto_execute cannot bypass escalation | ✅ | `test_executor_security.py::TestAutoExecuteCannotBypassEscalation` |
| Concurrent duplicate payment prevention | ✅ | `test_concurrency.py::TestConcurrentApprovalConsumption` |
| Audit chain integrity under load | ✅ | `test_concurrency.py::TestAuditChainConcurrency` |
| PQC-signed execution receipts | ✅ | `test_concurrency.py::TestPQCSignatureIntegrity` |
