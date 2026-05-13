import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from api.database import Base, get_db
from api.main import app

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
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


def assert_problem(response, expected_status: int):
    assert response.status_code == expected_status
    # FastAPI wraps HTTPException detail in {"detail": ...}
    body = response.json()
    error = body.get("detail", body) if isinstance(body, dict) else body
    assert isinstance(error, dict), f"RFC 9457: expected dict, got {type(error)}: {body}"
    assert "type" in error, f"RFC 9457: missing 'type'. Got: {body}"
    assert "title" in error, f"RFC 9457: missing 'title'. Got: {body}"
    assert "status" in error, f"RFC 9457: missing 'status'. Got: {body}"
    assert error["status"] == expected_status
