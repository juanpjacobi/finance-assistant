# Finance Assistant

Personal finance API with LLM integration via MCP and RAG.

## Architecture

This project follows a spec-first approach:
1. Always update `spec/openapi.yaml` before touching any code
2. Validate the spec with `spectral lint spec/openapi.yaml` — must have 0 errors
3. Keep `models.py`, `schemas.py` and `openapi.yaml` aligned at all times

## Developer workflow

The developer writes the spec. Claude implements. The flow is:

```
Edit openapi.yaml → spectral lint → /write-tests → /write-code → /write-frontend
```

## Skills

Before writing tests, code or frontend, always read the relevant skill first:

- **Adding or modifying endpoints** → read `skills/openapi-spec-reader/SKILL.md`
- **Writing tests** → `/write-tests` command (reads spec-reader + test-writer)
- **Implementing code** → `/write-code` command (reads spec-reader + code-generator)
- **Generating frontend** → `/write-frontend` command (reads spec-reader + frontend-generator)

## Stack

### Backend
- **FastAPI** — async REST API
- **SQLAlchemy** — async ORM
- **SQLite** — development database (`finance.db`)
- **PostgreSQL** — production database (change connection string in `database.py`)
- **MCP (FastMCP)** — exposes all API endpoints as LLM tools via `mcp_server/server.py`
- **ChromaDB** — vector database for document embeddings
- **LangChain** — RAG pipeline orchestration
- **Anthropic API** — LLM for document queries (`claude-sonnet-4-20250514`)
- **Python** — `venv/` virtualenv, dependencies in `requirements.txt`

### Frontend
- **Next.js 15** App Router + TypeScript + Tailwind CSS
- **sweetalert2** — confirmations and error notifications (never `window.confirm/alert`)
- Located at `../finance-assistant-frontend/`

## Project Structure

```
spec/                        OpenAPI 3.1 contract — source of truth
api/
  main.py                    FastAPI app, lifespan, CORS middleware
  database.py                SQLAlchemy async engine and session
  models.py                  Database tables (Category, Transaction, Budget, Document)
  schemas.py                 Pydantic schemas for request/response validation
  routers/
    categories.py
    transactions.py
    budgets.py               Monthly spending limits per category
    documents.py             PDF upload and RAG query endpoints
  rag/
    processor.py             PDF text extraction and ChromaDB indexing
    retriever.py             Semantic search and Claude query
mcp_server/
  server.py                  MCP server — tools map 1:1 to openapi.yaml operationIds
skills/
  openapi-spec-reader/       Parses OpenAPI spec into structured context
  openapi-test-writer/       Generates pytest integration tests from spec
  openapi-code-generator/    Generates FastAPI implementation from spec
  openapi-frontend-generator/ Generates Next.js types, API client and pages from spec
tests/
  conftest.py                Fixtures: async client, in-memory SQLite DB
  test_categories.py
  test_transactions.py
  test_budgets.py
  test_documents.py          Uses unittest.mock to avoid real ChromaDB/Anthropic calls
.claude/
  commands/
    read-spec.md             → /read-spec
    write-tests.md           → /write-tests
    write-code.md            → /write-code
    write-frontend.md        → /write-frontend
```

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Validate OpenAPI spec (must be 0 errors before touching code)
spectral lint spec/openapi.yaml

# Start API (development)
uvicorn api.main:app --reload

# Start MCP server
python3 mcp_server/server.py

# Run tests
pytest tests/ -v
```

## API Design Decisions

**Error format: RFC 9457 (Problem Details)**
All application errors use `raise HTTPException(status_code=X, detail={...})` with this structure:
```json
{
  "type": "https://api.financeassistant.dev/errors/not-found",
  "title": "Resource not found",
  "status": 404,
  "detail": "Transaction with id 42 does not exist"
}
```
FastAPI wraps this in `{"detail": {...}}` — always unwrap when reading the response body.

**Two types of 422 in FastAPI:**
- Pydantic validation (missing fields, wrong type) → `{"detail": [{"loc":..., "msg":...}]}` — not RFC 9457
- Business rule violation (raised manually) → `{"detail": {"type":..., "title":..., "status": 422}}` — RFC 9457

**Transactions belong to exactly one category.**

**Date defaults to today** when creating a transaction without `date`.

**Categories with transactions cannot be deleted** — returns 422.

**Path ordering matters.**
`/transactions/summary` is defined before `/transactions/{id}` to prevent routing conflicts.

**SQLAlchemy async relationships must use `selectinload`.**
Never access a relationship attribute without loading it explicitly — it raises `MissingGreenlet` in async context.

## MCP Design Decisions

**Tool names match operationIds exactly.**

**The MCP server calls the API via HTTP** — never imports DB code directly.

## RAG Design Decisions

**Each document has its own ChromaDB collection** (`document_{id}`).

**Claude answers only from retrieved chunks** — the prompt forbids general knowledge.

**In tests, `process_pdf` and `query_document` are mocked** to avoid needing real ChromaDB and Anthropic API calls.

## Frontend Design Decisions

**Server Components by default** — only `'use client'` when strictly needed (forms, interactivity).

**Server Components cannot pass functions as props to Client Components** — pass serializable data (`id`, `apiPath`) instead.

**React 19 event types** — use `{ preventDefault(): void }` instead of deprecated `React.FormEvent`.

**No dark mode** — `globals.css` has only `@import "tailwindcss"` and `font-family`. CSS variables for colors conflict with Tailwind explicit classes.

**Mobile-first** — tables wrapped in `overflow-x-auto`, grids start `grid-cols-1 sm:grid-cols-2`.

## Status

- [x] Backend API (categories, transactions, budgets, documents/RAG)
- [x] MCP server
- [x] Test suite (62 tests passing)
- [x] Skills (spec-reader, test-writer, code-generator, frontend-generator)
- [x] Frontend (list, create, edit, delete, document upload + RAG chat)
- [ ] Migrar a PostgreSQL (driver: asyncpg, cambio en database.py y requirements.txt)
- [ ] Dockerizar — Dockerfile backend + docker-compose con Postgres
- [ ] GitHub repos (backend y frontend separados)
- [ ] GitHub Actions CI/CD:
      - PR → corre pytest, bloquea merge si falla
      - Merge a main → build Docker image → push a registry (GHCR o Docker Hub) → deploy
- [ ] Deploy on Railway o Render (conectado al pipeline de Actions)
