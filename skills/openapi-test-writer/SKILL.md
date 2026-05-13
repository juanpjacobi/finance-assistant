---
name: openapi-test-writer
description: Generate pytest integration tests from an OpenAPI 3.x spec. Use this skill when asked to write, generate, or create tests for a FastAPI (or any Python HTTP) API that has an OpenAPI spec. Triggers include: "write tests", "generate tests", "create integration tests", "test the API", or any request to produce a test suite from a spec file. Always run openapi-spec-reader first to build spec context before generating tests.
---

This skill generates a complete pytest integration test suite from an OpenAPI spec. Tests run against a real database (not mocks) using httpx AsyncClient. Every operation in the spec gets at least one happy path test and one error path test.

## Prerequisites

Before writing any tests, the openapi-spec-reader skill must have been run. Its structured output is the input to this skill.

If spec context is not available, run:
```
SKILL: openapi-spec-reader
SPEC_PATH: {path/to/openapi.yaml}
```

## Inputs

```
SPEC_PATH:    path/to/openapi.yaml      (required)
APP_MODULE:   api.main:app              (required — FastAPI app import string)
DATABASE_URL: sqlite+aiosqlite:///:memory:  (optional — defaults to in-memory DB, fastest and cleanest)
OUTPUT_PATH:  tests/                    (optional — defaults to tests/)
```

## Setup: install dependencies

```bash
venv/bin/pip install pytest pytest-asyncio httpx
venv/bin/pip show pytest pytest-asyncio httpx | grep -E "^(Name|Version)" >> requirements.txt
```

## Test File Structure

Generate these files:

```
tests/
├── conftest.py          ← fixtures: app, client, db setup/teardown
├── test_{tag}.py        ← one file per OpenAPI tag
└── ...
```

## conftest.py template

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from {app_module_path}.database import Base, get_db
from {app_module_path}.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def client(db_engine):
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
```

Key decisions in this conftest:
- `scope="function"` — each test gets a clean database, no state leakage between tests
- Real SQLite DB (not mocks) — catches ORM bugs, constraint violations, relationship issues
- `dependency_overrides` — replaces production DB with test DB without touching app code

## Test Generation Rules

### For each GET list operation (e.g. listCategories):
```python
async def test_{operationId}_returns_empty_list(client):
    response = await client.get("/{path}")
    assert response.status_code == 200
    assert response.json() == []

async def test_{operationId}_returns_created_items(client):
    # create an item first
    await client.post(...)
    response = await client.get("/{path}")
    assert response.status_code == 200
    assert len(response.json()) == 1
```

### For each POST create operation:
```python
async def test_{operationId}_success(client):
    payload = {valid minimal payload from spec required fields}
    response = await client.post("/{path}", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["field"] == payload["field"]  # check each required field
    assert "id" in data
    assert "created_at" in data  # if in schema

async def test_{operationId}_missing_required_field(client):
    # omit each required field one at a time
    response = await client.post("/{path}", json={})
    assert response.status_code == 422

async def test_{operationId}_duplicate(client):
    # if spec description mentions uniqueness constraint
    payload = {...}
    await client.post("/{path}", json=payload)
    response = await client.post("/{path}", json=payload)
    assert response.status_code == 422
```

### For each GET single operation:
```python
async def test_{operationId}_success(client):
    created = (await client.post(...)).json()
    response = await client.get(f"/{path}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]

async def test_{operationId}_not_found(client):
    response = await client.get("/{path}/99999")
    assert response.status_code == 404
    # if RFC 9457 error format detected:
    error = response.json()
    assert "type" in error
    assert "title" in error
    assert error["status"] == 404
```

### For each PUT update operation:
```python
async def test_{operationId}_success(client):
    created = (await client.post(...)).json()
    response = await client.put(
        f"/{path}/{created['id']}",
        json={"field": "new_value"}
    )
    assert response.status_code == 200
    assert response.json()["field"] == "new_value"

async def test_{operationId}_partial_update(client):
    # only send one field, verify others unchanged
    created = (await client.post(..., json={...full payload...})).json()
    response = await client.put(
        f"/{path}/{created['id']}",
        json={"name": "updated"}
    )
    assert response.json()["name"] == "updated"
    assert response.json()["description"] == created["description"]  # unchanged

async def test_{operationId}_not_found(client):
    response = await client.put("/{path}/99999", json={...})
    assert response.status_code == 404
```

### For each DELETE operation:
```python
async def test_{operationId}_success(client):
    created = (await client.post(...)).json()
    response = await client.delete(f"/{path}/{created['id']}")
    assert response.status_code == 204
    # verify it's gone
    get_response = await client.get(f"/{path}/{created['id']}")
    assert get_response.status_code == 404

async def test_{operationId}_not_found(client):
    response = await client.delete("/{path}/99999")
    assert response.status_code == 404

async def test_{operationId}_conflict(client):
    # if spec mentions deletion constraint (e.g. "fails if transactions assigned")
    # set up the constraint condition first, then try to delete
    ...
    assert response.status_code == 422
```

### For filter/query operations:
```python
async def test_{operationId}_filter_by_{param}(client):
    # create items with different values
    # filter and verify only matching items returned
    ...
```

### For summary/aggregate operations:
```python
async def test_{operationId}_correct_calculation(client):
    # create known transactions
    # verify math is correct
    response = await client.get("/{path}", params={...})
    assert response.json()["total_income"] == expected_value
    assert response.json()["balance"] == expected_income - expected_expenses
```

## Error Format Assertions

If openapi-spec-reader detected RFC 9457 (`application/problem+json`):

```python
# Add this helper to conftest.py
def assert_problem(response, expected_status: int):
    assert response.status_code == expected_status
    # FastAPI wraps HTTPException detail in {"detail": {...}}
    body = response.json()
    error = body.get("detail", body) if isinstance(body, dict) else body
    assert isinstance(error, dict), f"RFC 9457: expected dict, got {type(error)}: {body}"
    assert "type" in error, f"RFC 9457: missing 'type'. Got: {body}"
    assert "title" in error, f"RFC 9457: missing 'title'. Got: {body}"
    assert "status" in error, f"RFC 9457: missing 'status'. Got: {body}"
    assert error["status"] == expected_status
```

**IMPORTANT — Two types of 422 in FastAPI:**

1. **Business logic 422** (raised with `raise HTTPException(status_code=422, detail={...})`):
   - Body: `{"detail": {"type": "...", "title": "...", "status": 422}}`
   - Use `assert_problem(response, 422)` ✓

2. **Pydantic validation 422** (missing required fields, invalid enum values — automatic):
   - Body: `{"detail": [{"loc": [...], "msg": "...", "type": "missing"}]}`
   - Does NOT follow RFC 9457 format
   - Use only `assert response.status_code == 422` — do NOT use `assert_problem`

Use in tests:
```python
assert_problem(response, 404)                    # not found — use assert_problem
assert_problem(response, 422)                    # business rule violation — use assert_problem
assert response.status_code == 422               # missing required field — just check status
```

## pytest.ini or pyproject.toml

Generate this config at project root:

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
pythonpath = .
```

The `pythonpath = .` is required so that `from api.xxx import ...` resolves correctly without needing `PYTHONPATH=.` prefix on every command.

## Execution

After generating tests, run them:

```bash
pytest tests/ -v
```

Expected output format:
```
tests/test_categories.py::test_listCategories_returns_empty_list PASSED
tests/test_categories.py::test_createCategory_success PASSED
tests/test_categories.py::test_createCategory_missing_required_field PASSED
...
```

If any test fails, analyze the failure before moving on. A failing test means either:
1. A bug in the implementation (fix the code)
2. A wrong assumption in the test (fix the test and document why)

Never delete a failing test to make the suite pass.

## Rules

- Every operationId gets at least 2 tests: happy path + at least one error path
- Tests must be independent: each test creates its own data, never relies on another test's state
- Use real assertions on response body fields, not just status codes
- If spec mentions a business rule, write a test that verifies it
- Never use `time.sleep()` — use async properly
- Test file names must match tag names: tag `categories` → `test_categories.py`
- All test functions must be `async def`
- Import only from the project, never hardcode internal implementation details