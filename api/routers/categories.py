from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from api.database import get_db
from api import models, schemas

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=list[schemas.CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Category))
    return result.scalars().all()

@router.post("", response_model=schemas.CategoryOut, status_code=201)
async def create_category(body: schemas.CategoryCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(models.Category).where(models.Category.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://api.financeassistant.dev/errors/duplicate",
                "title": "Duplicate category",
                "status": 422,
                "detail": f"Category '{body.name}' already exists",
            },
        )
    category = models.Category(**body.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category

@router.get("/{id}", response_model=schemas.CategoryOut)
async def get_category(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Category).where(models.Category.id == id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://api.financeassistant.dev/errors/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": f"Category with id {id} does not exist",
            },
        )
    return category

@router.put("/{id}", response_model=schemas.CategoryOut)
async def update_category(id: int, body: schemas.CategoryUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Category).where(models.Category.id == id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://api.financeassistant.dev/errors/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": f"Category with id {id} does not exist",
            },
        )
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category

@router.delete("/{id}", status_code=204)
async def delete_category(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Category)
        .where(models.Category.id == id)
        .options(selectinload(models.Category.transactions))
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://api.financeassistant.dev/errors/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": f"Category with id {id} does not exist",
            },
        )
    if category.transactions:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://api.financeassistant.dev/errors/conflict",
                "title": "Category in use",
                "status": 422,
                "detail": f"Category with id {id} has transactions assigned",
            },
        )
    await db.delete(category)
    await db.commit()