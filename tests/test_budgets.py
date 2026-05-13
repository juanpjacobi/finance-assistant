import pytest
from httpx import AsyncClient
from tests.conftest import assert_problem

BUDGET_URL = "/budgets"
CATEGORY_URL = "/categories"
TRANSACTION_URL = "/transactions"


async def create_category(client: AsyncClient, name="Test") -> int:
    response = await client.post(CATEGORY_URL, json={"name": name})
    return response.json()["id"]


def make_budget(category_id: int, monthly_limit=5000.0, month="2026-04"):
    return {"category_id": category_id, "monthly_limit": monthly_limit, "month": month}


# ─── listBudgets ──────────────────────────────────────────────────────────────

async def test_listBudgets_returns_empty_list(client: AsyncClient):
    response = await client.get(BUDGET_URL)
    assert response.status_code == 200
    assert response.json() == []


async def test_listBudgets_returns_created_items(client: AsyncClient):
    cat_id = await create_category(client)
    await client.post(BUDGET_URL, json=make_budget(cat_id, month="2026-04"))
    await client.post(BUDGET_URL, json=make_budget(cat_id, month="2026-05"))
    response = await client.get(BUDGET_URL)
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_listBudgets_filter_by_month(client: AsyncClient):
    cat_id = await create_category(client)
    await client.post(BUDGET_URL, json=make_budget(cat_id, month="2026-04"))
    await client.post(BUDGET_URL, json=make_budget(cat_id, month="2026-05"))
    response = await client.get(BUDGET_URL, params={"month": "2026-04"})
    data = response.json()
    assert len(data) == 1
    assert data[0]["month"] == "2026-04"


async def test_listBudgets_filter_by_category(client: AsyncClient):
    cat1 = await create_category(client, "Cat1")
    cat2 = await create_category(client, "Cat2")
    await client.post(BUDGET_URL, json=make_budget(cat1))
    await client.post(BUDGET_URL, json=make_budget(cat2))
    response = await client.get(BUDGET_URL, params={"category_id": cat1})
    data = response.json()
    assert len(data) == 1
    assert data[0]["category_id"] == cat1


# ─── createBudget ─────────────────────────────────────────────────────────────

async def test_createBudget_success(client: AsyncClient):
    cat_id = await create_category(client)
    response = await client.post(BUDGET_URL, json=make_budget(cat_id, monthly_limit=3000.0))
    assert response.status_code == 201
    data = response.json()
    assert data["category_id"] == cat_id
    assert data["monthly_limit"] == 3000.0
    assert data["month"] == "2026-04"
    assert "id" in data
    assert "created_at" in data


async def test_createBudget_missing_required_fields(client: AsyncClient):
    assert (await client.post(BUDGET_URL, json={})).status_code == 422


async def test_createBudget_invalid_category(client: AsyncClient):
    assert_problem(
        await client.post(BUDGET_URL, json=make_budget(99999)),
        404,
    )


async def test_createBudget_duplicate_category_month(client: AsyncClient):
    cat_id = await create_category(client)
    await client.post(BUDGET_URL, json=make_budget(cat_id, month="2026-04"))
    assert_problem(
        await client.post(BUDGET_URL, json=make_budget(cat_id, month="2026-04")),
        422,
    )


# ─── getBudget ────────────────────────────────────────────────────────────────

async def test_getBudget_success(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(BUDGET_URL, json=make_budget(cat_id))).json()
    response = await client.get(f"{BUDGET_URL}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_getBudget_not_found(client: AsyncClient):
    assert_problem(await client.get(f"{BUDGET_URL}/99999"), 404)


# ─── deleteBudget ─────────────────────────────────────────────────────────────

async def test_deleteBudget_success(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(BUDGET_URL, json=make_budget(cat_id))).json()
    response = await client.delete(f"{BUDGET_URL}/{created['id']}")
    assert response.status_code == 204
    assert_problem(await client.get(f"{BUDGET_URL}/{created['id']}"), 404)


async def test_deleteBudget_not_found(client: AsyncClient):
    assert_problem(await client.delete(f"{BUDGET_URL}/99999"), 404)


# ─── getBudgetStatus ──────────────────────────────────────────────────────────

async def test_getBudgetStatus_no_spending(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(BUDGET_URL, json=make_budget(cat_id, monthly_limit=5000.0, month="2026-04"))).json()
    response = await client.get(f"{BUDGET_URL}/{created['id']}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["spent"] == 0.0
    assert data["remaining"] == 5000.0
    assert data["exceeded"] is False


async def test_getBudgetStatus_with_spending(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(BUDGET_URL, json=make_budget(cat_id, monthly_limit=1000.0, month="2026-04"))).json()
    await client.post(TRANSACTION_URL, json={
        "amount": 300.0, "type": "expense", "category_id": cat_id, "date": "2026-04-10"
    })
    await client.post(TRANSACTION_URL, json={
        "amount": 200.0, "type": "expense", "category_id": cat_id, "date": "2026-04-20"
    })
    response = await client.get(f"{BUDGET_URL}/{created['id']}/status")
    data = response.json()
    assert data["spent"] == 500.0
    assert data["remaining"] == 500.0
    assert data["exceeded"] is False


async def test_getBudgetStatus_exceeded(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(BUDGET_URL, json=make_budget(cat_id, monthly_limit=100.0, month="2026-04"))).json()
    await client.post(TRANSACTION_URL, json={
        "amount": 150.0, "type": "expense", "category_id": cat_id, "date": "2026-04-05"
    })
    response = await client.get(f"{BUDGET_URL}/{created['id']}/status")
    data = response.json()
    assert data["spent"] == 150.0
    assert data["remaining"] == -50.0
    assert data["exceeded"] is True


async def test_getBudgetStatus_ignores_income(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(BUDGET_URL, json=make_budget(cat_id, monthly_limit=1000.0, month="2026-04"))).json()
    await client.post(TRANSACTION_URL, json={
        "amount": 500.0, "type": "income", "category_id": cat_id, "date": "2026-04-10"
    })
    response = await client.get(f"{BUDGET_URL}/{created['id']}/status")
    assert response.json()["spent"] == 0.0


async def test_getBudgetStatus_ignores_other_months(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(BUDGET_URL, json=make_budget(cat_id, monthly_limit=1000.0, month="2026-04"))).json()
    await client.post(TRANSACTION_URL, json={
        "amount": 500.0, "type": "expense", "category_id": cat_id, "date": "2026-03-15"
    })
    response = await client.get(f"{BUDGET_URL}/{created['id']}/status")
    assert response.json()["spent"] == 0.0


async def test_getBudgetStatus_not_found(client: AsyncClient):
    assert_problem(await client.get(f"{BUDGET_URL}/99999/status"), 404)
