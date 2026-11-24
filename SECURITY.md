# SentryFlow — Security Design

## Threat Model

| Threat | Trust Level | Mitigation |
|--------|-------------|------------|
| Manipulated model output (prompt injection) | Untrusted | 4-layer detection + independent deterministic policy engine |
| Compromised agent process | Untrusted | Container isolation, no access to protected resources |
| Supplier impersonation | Untrusted input | Validated against supplier registry, human verification |
| Invoice/payment fraud | Untrusted input | 3-way matching, duplicate detection, human approval |
| Approval replay/modification | Protected | Nonce-bound, parameter-canonical, single-use |
| Audit tampering | Protected | Hash chains, signed checkpoints, restricted write access |
| Insider abuse | Mitigated | Separation of duties, audit logging of all human actions |
| Host administrator compromise | **Out of scope** | Documented limitation; recommend FDE + HSM for production |
| Supply-chain attack | Partially mitigated | Dependency pinning, model hash verification |

## Authentication & Authorization

### 6 RBAC Roles

| Role | Can | Cannot |
|------|-----|--------|
| security_admin | Manage policies, agents, supplier verification | Approve financial transactions |
| procurement_operator | Submit documents, view agent activity | Approve transactions, modify policies |
| finance_approver | Approve/deny financial actions | Modify policies, register agents |
| security_analyst | View threats, audit log, run attack simulations | Modify policies, approve transactions |
| auditor | Read-only access to all audit records | Modify anything |
| agent | Submit tool calls via gateway (scoped by capabilities) | Approve own actions, impersonate humans |

### Auth Implementation
- **Passwords:** argon2id via argon2-cffi
- **Sessions:** JWT (HS256) — 1hr access, 24hr refresh
- **WebSocket:** Short-lived single-use tickets (not JWTs in query params)
- **Agent auth:** Ed25519-signed capability tokens

## Cryptographic Controls

### Signatures
- **Ed25519** (RFC 8032): all business records, agent tokens
- **ML-DSA-65** (FIPS 204): post-quantum signatures (hybrid mode)
- **Hybrid verification requires BOTH** when hybrid mode enabled — never silently downgrade

### Encryption
- **AES-256-GCM**: field-level encryption (bank accounts)
- **12-byte random nonce** per encryption operation (os.urandom(12))
- **ML-KEM-768** (FIPS 203): key encapsulation demonstration

### Integrity
- **SHA-256**: document content hashes, audit chain links
- **HMAC-SHA256**: bank account fingerprints (keyed, not plain SHA-256)
- **Canonical serialization**: JSON with sorted keys, no whitespace, UTF-8

## Approval Security

1. Approvals bind exact parameters (amount, supplier, bank account)
2. Nonces are cryptographically random and single-use
3. Consumed atomically in same DB transaction as action execution
4. Revalidation before execution checks: supplier, policy version, params, expiry
5. Agents cannot approve their own escalated actions
6. Expired approvals are rejected

## Audit Trail Security

- Append-only at application level (no UPDATE/DELETE API)
- Hash chain: each record links to previous via SHA-256
- Sequence gap detection (monotonic, no gaps)
- Signed checkpoints every N records (exportable)
- Structured decision summaries (never raw LLM reasoning)
- No credentials, raw bank account numbers, or unnecessary PII in logs

## Known Limitations

1. **Prompt injection is an unsolved problem.** Detection is defense-in-depth, not a guarantee. Novel attacks may bypass all layers. The policy engine is the authorization layer.
2. **Host admin compromise is out of scope.** A root-level attacker with Docker access can reach any container.
3. **All data is synthetic.** Gap exists between synthetic and real procurement data.
4. **SQLite concurrency limits.** WAL mode with single gateway process serializes writes. Acceptable for MVP.
5. **Audit is tamper-evident, not tamper-proof.** A privileged attacker with direct DB access and all signing keys could reconstruct a consistent chain.
6. **PQC algorithms are demonstration-grade.** pyca/cryptography is well-maintained but PQC standards are recent.
