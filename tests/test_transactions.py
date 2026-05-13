import pytest
from datetime import date
from httpx import AsyncClient
from tests.conftest import assert_problem

TRANSACTION_URL = "/transactions"
CATEGORY_URL = "/categories"


async def create_category(client: AsyncClient, name="Test") -> int:
    response = await client.post(CATEGORY_URL, json={"name": name})
    return response.json()["id"]


def make_transaction(category_id: int, amount=100.0, type="expense", **kwargs):
    return {"amount": amount, "type": type, "category_id": category_id, **kwargs}


# ─── listTransactions ─────────────────────────────────────────────────────────

async def test_listTransactions_returns_empty_list(client: AsyncClient):
    response = await client.get(TRANSACTION_URL)
    assert response.status_code == 200
    assert response.json() == []


async def test_listTransactions_returns_created_items(client: AsyncClient):
    cat_id = await create_category(client)
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id))
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id, amount=200.0))
    response = await client.get(TRANSACTION_URL)
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_listTransactions_filter_by_type(client: AsyncClient):
    cat_id = await create_category(client)
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id, type="income"))
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id, type="expense"))
    response = await client.get(TRANSACTION_URL, params={"type": "income"})
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "income"


async def test_listTransactions_filter_by_category(client: AsyncClient):
    cat1 = await create_category(client, "Cat1")
    cat2 = await create_category(client, "Cat2")
    await client.post(TRANSACTION_URL, json=make_transaction(cat1))
    await client.post(TRANSACTION_URL, json=make_transaction(cat2))
    response = await client.get(TRANSACTION_URL, params={"category_id": cat1})
    data = response.json()
    assert len(data) == 1
    assert data[0]["category_id"] == cat1


async def test_listTransactions_filter_by_date_range(client: AsyncClient):
    cat_id = await create_category(client)
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id, date="2026-01-15"))
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id, date="2026-03-10"))
    response = await client.get(TRANSACTION_URL, params={"date_from": "2026-01-01", "date_to": "2026-02-01"})
    assert len(response.json()) == 1


# ─── createTransaction ────────────────────────────────────────────────────────

async def test_createTransaction_success(client: AsyncClient):
    cat_id = await create_category(client)
    response = await client.post(TRANSACTION_URL, json=make_transaction(cat_id, amount=1500.0, type="income"))
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 1500.0
    assert data["type"] == "income"
    assert data["category_id"] == cat_id
    assert "id" in data
    assert "created_at" in data


async def test_createTransaction_date_defaults_to_today(client: AsyncClient):
    cat_id = await create_category(client)
    response = await client.post(TRANSACTION_URL, json=make_transaction(cat_id))
    assert response.status_code == 201
    assert response.json()["date"] == str(date.today())


async def test_createTransaction_with_explicit_date(client: AsyncClient):
    cat_id = await create_category(client)
    response = await client.post(TRANSACTION_URL, json=make_transaction(cat_id, date="2026-03-15"))
    assert response.json()["date"] == "2026-03-15"


async def test_createTransaction_missing_required_fields(client: AsyncClient):
    assert (await client.post(TRANSACTION_URL, json={})).status_code == 422


async def test_createTransaction_invalid_category(client: AsyncClient):
    assert_problem(
        await client.post(TRANSACTION_URL, json=make_transaction(99999)),
        404,
    )


async def test_createTransaction_invalid_type(client: AsyncClient):
    cat_id = await create_category(client)
    response = await client.post(TRANSACTION_URL, json=make_transaction(cat_id, type="invalid"))
    assert response.status_code == 422


# ─── getTransaction ───────────────────────────────────────────────────────────

async def test_getTransaction_success(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(TRANSACTION_URL, json=make_transaction(cat_id))).json()
    response = await client.get(f"{TRANSACTION_URL}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_getTransaction_not_found(client: AsyncClient):
    assert_problem(await client.get(f"{TRANSACTION_URL}/99999"), 404)


# ─── updateTransaction ────────────────────────────────────────────────────────

async def test_updateTransaction_success(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(TRANSACTION_URL, json=make_transaction(cat_id, amount=50.0))).json()
    response = await client.put(f"{TRANSACTION_URL}/{created['id']}", json={"amount": 999.0})
    assert response.status_code == 200
    assert response.json()["amount"] == 999.0


async def test_updateTransaction_partial_update_keeps_other_fields(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(TRANSACTION_URL, json=make_transaction(cat_id, amount=50.0, type="income", description="original"))).json()
    response = await client.put(f"{TRANSACTION_URL}/{created['id']}", json={"amount": 75.0})
    assert response.json()["amount"] == 75.0
    assert response.json()["type"] == "income"
    assert response.json()["description"] == "original"


async def test_updateTransaction_not_found(client: AsyncClient):
    assert_problem(await client.put(f"{TRANSACTION_URL}/99999", json={"amount": 1.0}), 404)


async def test_updateTransaction_invalid_category(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(TRANSACTION_URL, json=make_transaction(cat_id))).json()
    assert_problem(
        await client.put(f"{TRANSACTION_URL}/{created['id']}", json={"category_id": 99999}),
        404,
    )


# ─── deleteTransaction ────────────────────────────────────────────────────────

async def test_deleteTransaction_success(client: AsyncClient):
    cat_id = await create_category(client)
    created = (await client.post(TRANSACTION_URL, json=make_transaction(cat_id))).json()
    response = await client.delete(f"{TRANSACTION_URL}/{created['id']}")
    assert response.status_code == 204
    assert_problem(await client.get(f"{TRANSACTION_URL}/{created['id']}"), 404)


async def test_deleteTransaction_not_found(client: AsyncClient):
    assert_problem(await client.delete(f"{TRANSACTION_URL}/99999"), 404)


# ─── getTransactionSummary ────────────────────────────────────────────────────

async def test_getTransactionSummary_correct_calculation(client: AsyncClient):
    cat_id = await create_category(client)
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id, amount=1000.0, type="income", date="2026-04-01"))
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id, amount=300.0, type="expense", date="2026-04-15"))
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id, amount=200.0, type="expense", date="2026-04-20"))
    response = await client.get(f"{TRANSACTION_URL}/summary", params={"date_from": "2026-04-01", "date_to": "2026-04-30"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_income"] == 1000.0
    assert data["total_expenses"] == 500.0
    assert data["balance"] == 500.0


async def test_getTransactionSummary_empty_period(client: AsyncClient):
    response = await client.get(f"{TRANSACTION_URL}/summary", params={"date_from": "2026-01-01", "date_to": "2026-01-31"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_income"] == 0.0
    assert data["total_expenses"] == 0.0
    assert data["balance"] == 0.0


async def test_getTransactionSummary_missing_params(client: AsyncClient):
    assert (await client.get(f"{TRANSACTION_URL}/summary")).status_code == 422


async def test_getTransactionSummary_excludes_outside_range(client: AsyncClient):
    cat_id = await create_category(client)
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id, amount=500.0, type="income", date="2026-01-01"))
    await client.post(TRANSACTION_URL, json=make_transaction(cat_id, amount=100.0, type="income", date="2026-04-15"))
    response = await client.get(f"{TRANSACTION_URL}/summary", params={"date_from": "2026-04-01", "date_to": "2026-04-30"})
    assert response.json()["total_income"] == 100.0
