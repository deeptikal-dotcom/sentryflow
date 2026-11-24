# SentryFlow — Cryptographic Benchmark Results

**Date:** 2026-11-23
**Hardware:** Intel Core i5-1038NG7 @ 2.00GHz (4P/8T), 16 GB RAM
**OS:** macOS Darwin 24.6.0
**Python:** 3.15.2
**cryptography:** 50.0.2
**OpenSSL:** 4.1.0 (23 Oct 2026)

## PQC Capability Detection

| Algorithm | Available | Standard |
|-----------|-----------|----------|
| ML-DSA-65 | Yes | FIPS 204 |
| ML-KEM-768 | Yes | FIPS 203 |
| Ed25519 | Yes | RFC 8032 |
| AES-256-GCM | Yes | NIST SP 800-38D |

## Signature Operations

| Operation | Latency (ms/op) | Ops/sec |
|-----------|-----------------|---------|
| Ed25519 sign | 0.131 | 7,634 |
| Ed25519 verify | 0.181 | 5,525 |
| ML-DSA-65 sign | 0.485 | 2,062 |
| ML-DSA-65 verify | 0.144 | 6,944 |
| **Hybrid sign (Ed25519 + ML-DSA-65)** | **0.639** | **1,565** |
| **Hybrid verify** | **0.344** | **2,907** |

## Key Encapsulation (ML-KEM-768)

| Operation | Latency (ms/op) | Ops/sec |
|-----------|-----------------|---------|
| Keygen + Encapsulate | 0.332 | 3,012 |
| Decapsulate | 0.093 | 10,753 |

## Symmetric Operations

| Operation | Latency (ms/op) | Ops/sec |
|-----------|-----------------|---------|
| AES-256-GCM encrypt (32B plaintext) | 0.008 | 125,000 |
| AES-256-GCM decrypt (32B ciphertext) | 0.005 | 200,000 |
| HMAC-SHA256 fingerprint | 0.004 | 250,000 |

## Analysis

- **Full hybrid sign+verify cycle: ~1ms total.** This is negligible overhead for security gateway operations where network latency and policy evaluation dominate.
- **ML-DSA-65 verify is faster than Ed25519 verify** on this hardware, making hybrid verification practical for audit chain verification of large log sets.
- **ML-KEM-768 encapsulation is sub-millisecond**, confirming key exchange demonstrations are feasible.
- **AES-256-GCM and HMAC are effectively free** at the volumes SentryFlow processes (< 100 field-level encryptions per second in typical use).

## Notes

- All benchmarks run on CPU-only (no GPU acceleration used or needed for crypto operations).
- PQC algorithms are available natively via pyca/cryptography 50.0.2 linked against OpenSSL 4.1.0.
- These are actual measured values, not estimates.
- Ollama LLM benchmarks will be added when Ollama is installed (not currently available on host).
