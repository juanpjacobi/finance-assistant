---
name: openapi-code-generator
description: Generate FastAPI implementation code from an OpenAPI 3.x spec. Use this skill when asked to implement, generate, or create code for endpoints defined in a spec. Always run openapi-spec-reader first. Triggers include: "implement the spec", "generate the code", "write the router", "create the model".
---

This skill generates the full FastAPI implementation for endpoints defined in the OpenAPI spec that are not yet implemented. It follows the existing conventions of the project exactly.

## Prerequisites

openapi-spec-reader must have been run first. If not, run it now with the SPEC_PATH provided.

## Inputs

```
SPEC_PATH:   spec/openapi.yaml     (required)
APP_MODULE:  api.main:app          (required)
```

## Step 1 — Identify what needs to be implemented

Read the existing code to understand what already exists:

```bash
ls api/routers/
grep -n "class.*Base\b" api/models.py
grep -n "class.*Model\|__tablename__" api/models.py
grep -n "class.*Out\|class.*Create\|class.*Update" api/schemas.py
grep -n "include_router" api/main.py
```

Compare against the spec's operationIds. The gap between spec operations and existing routers is what needs to be generated.

## Step 2 — Generate models.py additions

For each new schema in the spec that maps to a database table:

Follow this pattern exactly (match the existing style in models.py):

```python
class NewModel(Base):
    __tablename__ = "new_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    optional_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fk_id: Mapped[int] = mapped_column(ForeignKey("other_table.id"), nullable=False)
    created_at: Mapped[datetime_] = mapped_column(DateTime, server_default=func.now())

    other: Mapped["OtherModel"] = relationship(back_populates="new_models")
```

Rules:
- Always use `Mapped[type]` annotation style
- Use `server_default=func.now()` for timestamps, never Python-side defaults
- Add `relationship()` both sides when FK exists
- Add back_populates to the related model too

## Step 3 — Generate schemas.py additions

For each new resource, generate three schemas following this pattern:

```python
class NewModelCreate(BaseModel):
    field: str
    optional_field: Optional[str] = None
    fk_id: int

class NewModelUpdate(BaseModel):
    field: Optional[str] = None
    optional_field: Optional[str] = None

class NewModelOut(BaseModel):
    id: int
    field: str
    optional_field: Optional[str] = None
    fk_id: int
    created_at: datetime_

    model_config = {"from_attributes": True}
```

Rules:
- `Create` — all required fields required, optional fields optional
- `Update` — all fields optional (partial update)
- `Out` — includes `id` and all fields returned by the spec schema
- Always add `model_config = {"from_attributes": True}` to `Out` schemas

## Step 4 — Generate router

Create `api/routers/{resource}.py` following this exact structure:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from api.database import get_db
from api import models, schemas

router = APIRouter(prefix="/{resources}", tags=["{resource}"])

@router.get("", response_model=list[schemas.{Resource}Out])
async def list_{resources}(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.{Resource}))
    return result.scalars().all()

@router.post("", response_model=schemas.{Resource}Out, status_code=201)
async def create_{resource}(body: schemas.{Resource}Create, db: AsyncSession = Depends(get_db)):
    obj = models.{Resource}(**body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

@router.get("/{id}", response_model=schemas.{Resource}Out)
async def get_{resource}(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.{Resource}).where(models.{Resource}.id == id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://api.financeassistant.dev/errors/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": f"{Resource} with id {id} does not exist",
            },
        )
    return obj

@router.delete("/{id}", status_code=204)
async def delete_{resource}(id: int, db: AsyncSession = Depends(get_db)):
    ...
```

Rules:
- Error format is always RFC 9457 (never plain strings)
- Always use `selectinload()` when accessing relationships (never lazy load)
- Use `model_dump(exclude_unset=True)` for partial updates
- 204 responses return nothing (no return statement or `return None`)

## Step 5 — Register router in main.py

Add to `api/main.py`:
```python
from api.routers import {resource}
app.include_router({resource}.router)
```

## Step 6 — Run tests

After generating all files:

```bash
PYTHONPATH=. venv/bin/pytest tests/ -v
```

If tests fail:
1. Read the failure carefully
2. Fix the code (never delete or weaken a test)
3. Run again until all pass

## Rules

- Never change existing code that already has passing tests
- Never use `lazy="dynamic"` or access relationships without `selectinload`
- Always match the naming conventions of the existing codebase exactly
- If a business rule is mentioned in the spec description, implement it
- Generate only what the spec defines — no extra fields or endpoints
