import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from api.database import engine, Base
from api.routers import categories, transactions, documents, budgets

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Finance Assistant API",
    version="1.0.0",
    description="Personal finance API with LLM integration",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(documents.router)
app.include_router(budgets.router)

if os.getenv("TESTING") == "true":
    @app.delete("/test/reset", status_code=204)
    async def reset_database():
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM budgets"))
            await conn.execute(text("DELETE FROM transactions"))
            await conn.execute(text("DELETE FROM documents"))
            await conn.execute(text("DELETE FROM categories"))