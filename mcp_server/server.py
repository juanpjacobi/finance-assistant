from datetime import date
import httpx
from mcp.server.fastmcp import FastMCP

API_BASE_URL = "http://localhost:8000"

mcp = FastMCP("Finance Assistant")

# ─── CATEGORIES ───────────────────────────────────────────

@mcp.tool()
async def listCategories() -> dict:
    """List all available categories for classifying transactions."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/categories")
        return response.json()

@mcp.tool()
async def createCategory(name: str, description: str = None) -> dict:
    """Create a new category. Name must be unique."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/categories",
            json={"name": name, "description": description},
        )
        return response.json()

@mcp.tool()
async def getCategory(id: int) -> dict:
    """Get a single category by its id."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/categories/{id}")
        return response.json()

@mcp.tool()
async def updateCategory(id: int, name: str = None, description: str = None) -> dict:
    """Update name or description of an existing category."""
    async with httpx.AsyncClient() as client:
        body = {k: v for k, v in {"name": name, "description": description}.items() if v is not None}
        response = await client.put(f"{API_BASE_URL}/categories/{id}", json=body)
        return response.json()

@mcp.tool()
async def deleteCategory(id: int) -> dict:
    """Delete a category. Fails if transactions are assigned to it."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_BASE_URL}/categories/{id}")
        if response.status_code == 204:
            return {"success": True}
        return response.json()

# ─── TRANSACTIONS ──────────────────────────────────────────

@mcp.tool()
async def listTransactions(
    type: str = None,
    category_id: int = None,
    date_from: str = None,
    date_to: str = None,
) -> dict:
    """
    List transactions with optional filters.
    - type: 'income' or 'expense'
    - category_id: filter by category
    - date_from / date_to: date range in YYYY-MM-DD format
    """
    async with httpx.AsyncClient() as client:
        params = {k: v for k, v in {
            "type": type,
            "category_id": category_id,
            "date_from": date_from,
            "date_to": date_to,
        }.items() if v is not None}
        response = await client.get(f"{API_BASE_URL}/transactions", params=params)
        return response.json()

@mcp.tool()
async def createTransaction(
    amount: float,
    type: str,
    category_id: int,
    description: str = None,
    date: str = None,
) -> dict:
    """
    Create a new transaction.
    - type: 'income' or 'expense'
    - date: YYYY-MM-DD format, defaults to today if not provided
    """
    async with httpx.AsyncClient() as client:
        body = {k: v for k, v in {
            "amount": amount,
            "type": type,
            "category_id": category_id,
            "description": description,
            "date": date,
        }.items() if v is not None}
        response = await client.post(f"{API_BASE_URL}/transactions", json=body)
        return response.json()

@mcp.tool()
async def getTransaction(id: int) -> dict:
    """Get a single transaction by its id."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/transactions/{id}")
        return response.json()

@mcp.tool()
async def updateTransaction(
    id: int,
    amount: float = None,
    type: str = None,
    category_id: int = None,
    description: str = None,
    date: str = None,
) -> dict:
    """Update one or more fields of an existing transaction."""
    async with httpx.AsyncClient() as client:
        body = {k: v for k, v in {
            "amount": amount,
            "type": type,
            "category_id": category_id,
            "description": description,
            "date": date,
        }.items() if v is not None}
        response = await client.put(f"{API_BASE_URL}/transactions/{id}", json=body)
        return response.json()

@mcp.tool()
async def deleteTransaction(id: int) -> dict:
    """Permanently delete a transaction by its id."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_BASE_URL}/transactions/{id}")
        if response.status_code == 204:
            return {"success": True}
        return response.json()

@mcp.tool()
async def getTransactionSummary(date_from: str, date_to: str) -> dict:
    """
    Get financial summary for a period.
    Returns total income, total expenses and balance.
    - date_from / date_to: required, format YYYY-MM-DD
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/transactions/summary",
            params={"date_from": date_from, "date_to": date_to},
        )
        return response.json()
    
@mcp.tool()
async def uploadDocument(file_path: str) -> dict:
    """Upload a PDF document for semantic search. Provide the absolute file path."""
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                f"{API_BASE_URL}/documents",
                files={"file": (file_path.split("/")[-1], f, "application/pdf")},
                timeout=30.0,
            )
        return response.json()

@mcp.tool()
async def queryDocument(document_id: int, question: str) -> dict:
    """
    Ask a question about a previously uploaded document.
    Use getDocuments first to find the document_id.
    - document_id: the id returned when the document was uploaded
    - question: the question to ask about the document content
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/documents/{document_id}/query",
            json={"question": question},
            timeout=30.0,
        )
        return response.json()

if __name__ == "__main__":
    mcp.run()