# Knowledge Chat

> A secure, multi-tenant Retrieval-Augmented Generation platform for private document intelligence.

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Next.js-Frontend-000000?logo=nextdotjs&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/MySQL-Persistence-4479A1?logo=mysql&logoColor=white" alt="MySQL">
  <img src="https://img.shields.io/badge/Redis-Rate%20Limiting-DC382D?logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/Chroma-Vector%20Store-6C63FF" alt="Chroma">
  <img src="https://img.shields.io/badge/Gemini-LLM-4285F4?logo=google&logoColor=white" alt="Gemini">
</p>

## Overview

Knowledge Chat is a full-stack RAG application that allows authenticated teams to upload private PDF documents, retrieve semantically relevant content, and generate grounded answers through an LLM.

Unlike a basic RAG demo, this project includes the operational features required for a serious product foundation:

- multi-tenant organization isolation,
- JWT authentication and refresh tokens,
- role-based access control,
- document ownership and lifecycle management,
- Redis-backed rate limiting,
- structured logging and request tracing,
- liveness and readiness probes,
- OpenAPI contract validation,
- a responsive ChatGPT-style frontend,
- and a tested backend architecture.

It is suitable as a foundation for internal knowledge assistants, enterprise search, research portals, legal-document analysis, policy assistants, and domain-specific AI copilots.

> Current chat history is stored locally in the browser. Each RAG request is currently processed independently; server-side conversational memory is included in the roadmap.

---

## Screenshots

### Login Page

<img width="1916" height="922" alt="1" src="https://github.com/user-attachments/assets/e6d9343a-4a31-4e42-bf27-1b6c74b6c01b" />


### Chat Interface

<img width="1920" height="922" alt="2" src="https://github.com/user-attachments/assets/02ac4711-f76a-4736-9c24-54c71eea23c3" />


### Document Management

<img width="1920" height="920" alt="3" src="https://github.com/user-attachments/assets/ddf131b7-eea2-4ef2-bb79-0d87053a386d" />


### Team Management

<img width="1920" height="923" alt="4" src="https://github.com/user-attachments/assets/1d144fca-26db-4405-95f7-47ef7a32e0d3" />

---

## Product Highlights

### AI and RAG

- PDF ingestion and text extraction
- Configurable text chunking
- Hugging Face sentence embeddings
- Chroma vector retrieval
- Google Gemini answer generation
- Knowledge-base and document filtering
- Source-aware responses
- Configurable top-k retrieval

### Authentication and Multi-Tenancy

- User registration and login
- JWT access tokens
- Refresh-token workflow
- Logout support
- Database-backed users
- Organization memberships
- Tenant-aware access controls
- Active-membership validation

### Role-Based Authorization

| Operation | Owner | Admin | Member | Viewer |
|---|---:|---:|---:|---:|
| Query RAG | Yes | Yes | Yes | Yes |
| View documents | Yes | Yes | Yes | Yes |
| Upload documents | Yes | Yes | Yes | No |
| Delete documents | Yes | Yes | Yes | No |
| Manage members | Yes | Yes | No | No |

### Document Management

- Upload PDF documents
- List and filter documents
- View document metadata
- Restrict access by organization and user
- Delete database records
- Remove related vectors from Chroma

### Security and Reliability

- JWT authentication
- Tenant isolation
- Role-based permissions
- Redis-backed request limits
- Login brute-force protection
- Registration abuse protection
- Upload and RAG query limits
- Restricted CORS
- Trusted-host validation
- Security response headers
- Standardized API errors
- Request IDs
- Structured logs
- Health and readiness endpoints
- Fail-closed rate-limit policy

### Frontend Experience

- ChatGPT-style responsive sidebar
- New chat
- Recent chat search
- Local chat history
- Chat deletion
- PDF upload
- Document selection
- Knowledge-base selection
- Team management
- Role updates
- Light and dark themes
- Authentication and token refresh
- Rate-limit feedback
- Backend health display

---

## Architecture

```mermaid
flowchart LR
    U[Browser] --> F[Next.js Frontend]
    F -->|REST + JWT| A[FastAPI API]

    A --> AUTH[Authentication and RBAC]
    A --> DOC[Document Service]
    A --> RAG[RAG Service]
    A --> RATE[Redis Rate Limiting]

    AUTH --> DB[(MySQL)]
    DOC --> DB
    DOC --> V[(Chroma)]
    RAG --> V
    RAG --> E[Embeddings]
    RAG --> L[Google Gemini]
```

### Document ingestion flow

```text
Authenticated user
        ↓
Tenant and role validation
        ↓
PDF upload
        ↓
Text extraction and chunking
        ↓
Embedding generation
        ↓
Chroma vector storage
        ↓
MySQL metadata storage
```

### RAG query flow

```text
Authenticated user
        ↓
Membership validation
        ↓
Redis rate-limit check
        ↓
Query embedding
        ↓
Vector similarity search
        ↓
Relevant document context
        ↓
Grounded LLM generation
        ↓
Answer and sources
```

---

## Scalability

The project is designed for scalable deployment through clear service boundaries and externalized state.

### Stateless API layer

JWT access-token validation allows multiple FastAPI instances to serve requests behind a load balancer.

### Async I/O

FastAPI and async SQLAlchemy reduce blocking during database and network operations.

### Shared infrastructure

Persistent and distributed state is separated into dedicated services:

- MySQL for application metadata
- Redis for distributed rate-limit counters
- Chroma for vector retrieval
- external embedding and LLM providers

### Horizontal scaling path

```text
Load Balancer
    ├── FastAPI Instance 1
    ├── FastAPI Instance 2
    └── FastAPI Instance N

Shared services:
    MySQL
    Redis
    Vector Database
    Object Storage
```

### Deployment health checks

- `/api/v1/health/live` confirms the API process is alive
- `/api/v1/health/ready` confirms MySQL and Redis are available

> The architecture is prepared for scaling, but production capacity should be validated with workload-specific load testing.

---

## Technology Stack

### Backend

- Python 3.12
- FastAPI
- SQLAlchemy Async
- Alembic
- Pydantic
- MySQL
- Redis
- Chroma
- Hugging Face sentence transformers
- Google Gemini
- Structlog
- JWT authentication

### Frontend

- Next.js
- React
- TypeScript
- App Router
- Lucide React
- React Markdown
- GitHub Flavored Markdown

### Infrastructure

- Docker
- Uvicorn
- OpenAPI
- Redis persistence
- MySQL migrations

---

## Project Structure

```text
rag_app/
├── backend/
│   └── app/
│       ├── api/
│       ├── core/
│       ├── database/
│       ├── models/
│       ├── rate_limiting/
│       ├── repositories/
│       ├── schemas/
│       └── services/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── types/
├── frontend_contract/
│   ├── README.md
│   ├── frontend.env.example
│   └── openapi.json
├── scripts/
├── tests/
├── alembic/
└── pyproject.toml
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- `uv`
- Node.js LTS
- Docker Desktop
- MySQL
- Redis

### Backend

```powershell
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY

uv sync
uv run alembic upgrade head
uv run uvicorn backend.app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### Redis

```powershell
docker run -d `
    --name rag-redis `
    --restart unless-stopped `
    -p 6379:6379 `
    -v rag_redis_data:/data `
    redis:7-alpine `
    redis-server --appendonly yes
```

### Frontend

```powershell
cd frontend

corepack pnpm@11.9.0 install `
    --fetch-timeout=600000 `
    --fetch-retries=5 `
    --network-concurrency=4

corepack pnpm@11.9.0 run dev
```

Frontend:

```text
http://localhost:3000
```

---

## Environment Configuration

Backend `.env` example:

```env
APP_NAME=Knowledge Chat
APP_ENVIRONMENT=development
API_PREFIX=/api/v1

DATABASE_URL=mysql+aiomysql://USER:PASSWORD@127.0.0.1:3306/rag_app

REDIS_URL=redis://127.0.0.1:6379/0
RATE_LIMIT_ENABLED=true
RATE_LIMIT_FAIL_OPEN=false

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256

GOOGLE_API_KEY=replace-with-your-api-key
GEMINI_MODEL=gemini-2.5-flash
```

Frontend `.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Never commit real credentials or secrets.

---

## API Overview

### Authentication

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

### Organizations

```text
GET    /api/v1/organizations/current
GET    /api/v1/organizations/current/members
POST   /api/v1/organizations/current/members
PATCH  /api/v1/organizations/current/members/{membership_id}/role
DELETE /api/v1/organizations/current/members/{membership_id}
```

### Documents

```text
POST   /api/v1/documents
GET    /api/v1/documents
GET    /api/v1/documents/{document_id}
DELETE /api/v1/documents/{document_id}
```

### RAG

```text
POST /api/v1/rag/query
```

### Health

```text
GET /api/v1/health
GET /api/v1/health/live
GET /api/v1/health/ready
```

---

## Rate Limits

| Scope | Default Limit |
|---|---:|
| General API | 300 requests/minute/IP |
| Registration | 5 requests/hour/IP |
| Login | 10 requests/15 minutes/IP |
| Refresh | 30 requests/10 minutes/IP |
| Upload | 20 requests/hour/user |
| RAG query | 60 requests/minute/user |

Rate-limited responses include:

```text
HTTP 429 Too Many Requests
Retry-After
X-RateLimit-Limit
X-RateLimit-Remaining
X-RateLimit-Reset
```

---

## Standard Error Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message.",
    "details": null
  }
}
```

Common status codes:

```text
400 Invalid request
401 Authentication failure
403 Authorization failure
404 Resource not found
409 Conflict
422 Validation error
429 Rate limit exceeded
500 Internal server error
503 Dependency unavailable
```

---

## Testing

Backend quality gate:

```powershell
uv run python -m tests.test_backend_contract
uv run python -m tests.test_health_endpoints
uv run python -m tests.test_rate_limiting
uv run python -m tests.test_security_middleware
uv run python -m tests.test_document_management
uv run python -m tests.test_document_repository
uv run python -m tests.test_membership_foundation
uv run python -m tests.test_role_authorization
uv run python -m tests.test_real_auth_flow
uv run python -m tests.test_jwt_auth
uv run python -m tests.test_api_endpoints
```

Frontend checks:

```powershell
corepack pnpm@11.9.0 run typecheck
corepack pnpm@11.9.0 run build
```

---

## Security Status

Implemented:

- database-backed authentication,
- JWT access and refresh flow,
- tenant isolation,
- role-based access controls,
- Redis rate limits,
- trusted hosts,
- CORS restrictions,
- security headers,
- request tracing,
- structured errors,
- dependency readiness checks.

Recommended before public production deployment:

- HTTPS/TLS,
- managed secret storage,
- provider-level quota handling,
- daily and monthly LLM budgets,
- concurrency limits,
- audit logs,
- malware scanning,
- stricter PDF validation,
- prompt-injection defenses,
- monitoring and alerts,
- backup and disaster recovery.

---

## Current Limitations

- Chat history is stored in browser local storage.
- Previous messages are not yet added automatically to the RAG prompt.
- Server-side conversation and message records are not yet implemented.
- LLM provider quotas are not yet mirrored as organization-level budgets.
- Production load-test results are not yet published.

These limitations are documented intentionally and are part of the roadmap.

---

## Roadmap

- Server-side conversations and messages
- Conversation-aware RAG
- History-based query rewriting
- Streaming responses
- Daily and monthly LLM quotas
- Token and cost analytics
- Provider 429 retry handling
- Concurrency control
- Audit logging
- Background ingestion workers
- Object storage
- Queue-based document processing
- Prompt-injection protection
- Malware scanning
- Password reset
- Email invitations
- Multi-format document ingestion
- Docker Compose
- CI/CD
- Cloud deployment templates

---

## Use Cases

- Internal company knowledge assistant
- Research-paper Q&A
- Legal-document search
- Compliance and policy assistant
- Technical documentation chatbot
- University knowledge portal
- Customer-support knowledge base
- Contract and proposal analysis
- Private team AI workspace

---

## OpenAPI Contract

```text
frontend_contract/openapi.json
```

Frontend integration guide:

```text
frontend_contract/README.md
```

---

## Screenshots

Add screenshots under `docs/screenshots/`, then include:

```markdown
![Chat interface](docs/screenshots/chat.png)
![Document management](docs/screenshots/documents.png)
![Team management](docs/screenshots/team.png)
```

---

## License

Add a license before publishing:

- MIT for broad reuse
- Apache 2.0 for permissive use with explicit patent terms
- A proprietary license for commercial client work

Without a license, all rights remain reserved by default.

---

## Author

**Anjum Zahid**

- GitHub: `@anjumzahid`

---

## Final Note

Knowledge Chat demonstrates how a RAG system can move beyond a prototype by combining AI retrieval with tenant isolation, role-based security, operational safeguards, health checks, a complete frontend, and a validated API contract.

If this project helps you, consider starring the repository.
