import pytest
from httpx import AsyncClient
from tests.conftest import assert_problem

CATEGORY_URL = "/categories"


def make_category(name="Alimentación", description=None):
    payload = {"name": name}
    if description:
        payload["description"] = description
    return payload


# ─── listCategories ───────────────────────────────────────────────────────────

async def test_listCategories_returns_empty_list(client: AsyncClient):
    response = await client.get(CATEGORY_URL)
    assert response.status_code == 200
    assert response.json() == []


async def test_listCategories_returns_created_items(client: AsyncClient):
    await client.post(CATEGORY_URL, json=make_category("Transporte"))
    await client.post(CATEGORY_URL, json=make_category("Salud"))
    response = await client.get(CATEGORY_URL)
    assert response.status_code == 200
    assert len(response.json()) == 2


# ─── createCategory ───────────────────────────────────────────────────────────

async def test_createCategory_success(client: AsyncClient):
    response = await client.post(CATEGORY_URL, json=make_category("Alimentación", "Comida y bebida"))
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alimentación"
    assert data["description"] == "Comida y bebida"
    assert "id" in data


async def test_createCategory_without_description(client: AsyncClient):
    response = await client.post(CATEGORY_URL, json={"name": "Transporte"})
    assert response.status_code == 201
    assert response.json()["description"] is None


async def test_createCategory_missing_name(client: AsyncClient):
    response = await client.post(CATEGORY_URL, json={})
    assert response.status_code == 422


async def test_createCategory_duplicate_name(client: AsyncClient):
    await client.post(CATEGORY_URL, json=make_category("Salud"))
    response = await client.post(CATEGORY_URL, json=make_category("Salud"))
    assert_problem(response, 422)


# ─── getCategory ──────────────────────────────────────────────────────────────

async def test_getCategory_success(client: AsyncClient):
    created = (await client.post(CATEGORY_URL, json=make_category("Ocio"))).json()
    response = await client.get(f"{CATEGORY_URL}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["name"] == "Ocio"


async def test_getCategory_not_found(client: AsyncClient):
    assert_problem(await client.get(f"{CATEGORY_URL}/99999"), 404)


# ─── updateCategory ───────────────────────────────────────────────────────────

async def test_updateCategory_success(client: AsyncClient):
    created = (await client.post(CATEGORY_URL, json=make_category("Viajes"))).json()
    response = await client.put(f"{CATEGORY_URL}/{created['id']}", json={"name": "Viajes y Turismo"})
    assert response.status_code == 200
    assert response.json()["name"] == "Viajes y Turismo"


async def test_updateCategory_partial_update_keeps_other_fields(client: AsyncClient):
    created = (await client.post(CATEGORY_URL, json=make_category("Tecnología", "Gadgets"))).json()
    response = await client.put(f"{CATEGORY_URL}/{created['id']}", json={"name": "Tech"})
    assert response.json()["name"] == "Tech"
    assert response.json()["description"] == "Gadgets"


async def test_updateCategory_not_found(client: AsyncClient):
    assert_problem(await client.put(f"{CATEGORY_URL}/99999", json={"name": "X"}), 404)


# ─── deleteCategory ───────────────────────────────────────────────────────────

async def test_deleteCategory_success(client: AsyncClient):
    created = (await client.post(CATEGORY_URL, json=make_category("Temporal"))).json()
    response = await client.delete(f"{CATEGORY_URL}/{created['id']}")
    assert response.status_code == 204
    assert_problem(await client.get(f"{CATEGORY_URL}/{created['id']}"), 404)


async def test_deleteCategory_not_found(client: AsyncClient):
    assert_problem(await client.delete(f"{CATEGORY_URL}/99999"), 404)


async def test_deleteCategory_with_transactions_fails(client: AsyncClient):
    category = (await client.post(CATEGORY_URL, json=make_category("Con transacciones"))).json()
    await client.post("/transactions", json={
        "amount": 100.0,
        "type": "expense",
        "category_id": category["id"],
    })
    assert_problem(await client.delete(f"{CATEGORY_URL}/{category['id']}"), 422)
