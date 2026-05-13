import io
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from tests.conftest import assert_problem

# NOTE: spec defines POST /documents/upload but router serves at POST /documents.
# Tests run against the actual implementation path.
DOCUMENT_URL = "/documents"


def make_pdf_upload(filename="test.pdf"):
    content = b"%PDF-1.4 fake pdf content"
    return {"file": (filename, io.BytesIO(content), "application/pdf")}


# ─── uploadDocument ───────────────────────────────────────────────────────────

async def test_uploadDocument_success(client: AsyncClient):
    with patch("api.routers.documents.process_pdf", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = 5
        response = await client.post(DOCUMENT_URL, files=make_pdf_upload("estado_abril.pdf"))
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "estado_abril.pdf"
    assert data["status"] == "ready"
    assert "id" in data
    assert "uploaded_at" in data


async def test_uploadDocument_non_pdf_rejected(client: AsyncClient):
    files = {"file": ("document.txt", io.BytesIO(b"not a pdf"), "text/plain")}
    response = await client.post(DOCUMENT_URL, files=files)
    assert_problem(response, 422)


async def test_uploadDocument_process_error_sets_status_error(client: AsyncClient):
    with patch("api.routers.documents.process_pdf", new_callable=AsyncMock) as mock_process:
        mock_process.side_effect = Exception("ChromaDB unavailable")
        response = await client.post(DOCUMENT_URL, files=make_pdf_upload())
    assert response.status_code == 201
    assert response.json()["status"] == "error"


# ─── queryDocument ────────────────────────────────────────────────────────────

async def test_queryDocument_success(client: AsyncClient):
    with patch("api.routers.documents.process_pdf", new_callable=AsyncMock, return_value=3):
        upload = (await client.post(DOCUMENT_URL, files=make_pdf_upload())).json()

    with patch("api.routers.documents.query_document", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = "El total fue $1500."
        response = await client.post(
            f"{DOCUMENT_URL}/{upload['id']}/query",
            json={"question": "¿Cuál fue el total?"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "¿Cuál fue el total?"
    assert data["answer"] == "El total fue $1500."


async def test_queryDocument_not_found(client: AsyncClient):
    assert_problem(
        await client.post(f"{DOCUMENT_URL}/99999/query", json={"question": "¿Algo?"}),
        404,
    )


async def test_queryDocument_document_not_ready(client: AsyncClient):
    with patch("api.routers.documents.process_pdf", new_callable=AsyncMock) as mock_process:
        mock_process.side_effect = Exception("fail")
        upload = (await client.post(DOCUMENT_URL, files=make_pdf_upload())).json()

    assert upload["status"] == "error"
    assert_problem(
        await client.post(f"{DOCUMENT_URL}/{upload['id']}/query", json={"question": "¿Algo?"}),
        422,
    )


async def test_queryDocument_missing_question(client: AsyncClient):
    with patch("api.routers.documents.process_pdf", new_callable=AsyncMock, return_value=3):
        upload = (await client.post(DOCUMENT_URL, files=make_pdf_upload())).json()
    response = await client.post(f"{DOCUMENT_URL}/{upload['id']}/query", json={})
    assert response.status_code == 422
