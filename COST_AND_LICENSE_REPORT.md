# SentryFlow — Cost and License Report

## Zero-Cost Operation Verification

SentryFlow operates with **zero recurring costs**:

| Category | Status | Details |
|----------|--------|---------|
| Cloud APIs | ✅ None | No OpenAI, Anthropic, Gemini, or other paid APIs |
| Cloud services | ✅ None | No AWS, GCP, Azure dependencies |
| Commercial LLMs | ✅ None | Ollama with open-weight models (Phi-4-mini, Llama 3.2 3B) |
| Database | ✅ Free | SQLite (embedded, no server) |
| Hosting | ✅ Self-hosted | Docker Compose on any Linux/Mac machine |
| Certificates | ✅ Free | Self-signed or Let's Encrypt for production |

## Dependency License Audit

All dependencies use commercially compatible licenses as required by CLAUDE.md.

### Backend (Python)

| Package | Version | License | Compatible |
|---------|---------|---------|------------|
| fastapi | 0.165.0 | MIT | ✅ |
| uvicorn | 0.54.0 | BSD-3-Clause | ✅ |
| SQLAlchemy | 2.1.9 | MIT | ✅ |
| aiosqlite | 0.22.1 | MIT | ✅ |
| pydantic | 2.14.4 | MIT | ✅ |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | ✅ |
| argon2-cffi | 25.1.0 | MIT | ✅ |
| python-jose | 3.5.0 | MIT | ✅ |
| httpx | 0.28.1 | BSD-3-Clause | ✅ |
| pypdf | 7.1.1 | BSD-3-Clause | ✅ |
| python-multipart | 0.0.34 | Apache-2.0 | ✅ |
| pytest | 9.2.0 | MIT | ✅ |
| pytest-asyncio | 1.5.0 | Apache-2.0 | ✅ |

### Frontend (TypeScript)

| Package | License | Compatible |
|---------|---------|------------|
| React | MIT | ✅ |
| TypeScript | Apache-2.0 | ✅ |
| Vite | MIT | ✅ |
| TailwindCSS | MIT | ✅ |
| Recharts | MIT | ✅ |
| lucide-react | ISC | ✅ |
| react-router-dom | MIT | ✅ |

### Explicitly Avoided

| Package | License | Reason |
|---------|---------|--------|
| PyMuPDF (fitz) | AGPL-3.0 | Copyleft, incompatible with commercial use |
| Redis 7.4+ | RSALv2 | Not open-source compatible |
| OpenAI API | Proprietary | Paid, cloud-dependent |
| Anthropic API | Proprietary | Paid, cloud-dependent |
| Gemini API | Proprietary | Paid, cloud-dependent |

## Conclusion

All 13+ backend and 7+ frontend dependencies use MIT, Apache-2.0, BSD-3-Clause, or ISC licenses. No AGPL, GPL, RSALv2, or proprietary dependencies are included. Zero recurring costs for operation.
