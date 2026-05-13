from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from api.database import get_db
from api import models, schemas

router = APIRouter(prefix="/budgets", tags=["budgets"])


async def get_budget_or_404(id: int, db: AsyncSession) -> models.Budget:
    result = await db.execute(select(models.Budget).where(models.Budget.id == id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://api.financeassistant.dev/errors/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": f"Budget with id {id} does not exist",
            },
        )
    return budget


@router.get("", response_model=list[schemas.BudgetOut])
async def list_budgets(
    month: str | None = Query(None),
    category_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(models.Budget)
    if month:
        query = query.where(models.Budget.month == month)
    if category_id:
        query = query.where(models.Budget.category_id == category_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=schemas.BudgetOut, status_code=201)
async def create_budget(body: schemas.BudgetCreate, db: AsyncSession = Depends(get_db)):
    category = await db.execute(
        select(models.Category).where(models.Category.id == body.category_id)
    )
    if not category.scalar_one_or_none():
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://api.financeassistant.dev/errors/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": f"Category with id {body.category_id} does not exist",
            },
        )
    budget = models.Budget(**body.model_dump())
    db.add(budget)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://api.financeassistant.dev/errors/duplicate",
                "title": "Duplicate budget",
                "status": 422,
                "detail": f"A budget for category {body.category_id} in {body.month} already exists",
            },
        )
    await db.refresh(budget)
    return budget


@router.get("/{id}", response_model=schemas.BudgetOut)
async def get_budget(id: int, db: AsyncSession = Depends(get_db)):
    return await get_budget_or_404(id, db)


@router.delete("/{id}", status_code=204)
async def delete_budget(id: int, db: AsyncSession = Depends(get_db)):
    budget = await get_budget_or_404(id, db)
    await db.delete(budget)
    await db.commit()


@router.get("/{id}/status", response_model=schemas.BudgetStatusOut)
async def get_budget_status(id: int, db: AsyncSession = Depends(get_db)):
    budget = await get_budget_or_404(id, db)

    month_start = f"{budget.month}-01"
    month_end = f"{budget.month}-31"

    result = await db.execute(
        select(func.coalesce(func.sum(models.Transaction.amount), 0.0)).where(
            models.Transaction.category_id == budget.category_id,
            models.Transaction.type == models.TransactionType.expense,
            models.Transaction.date >= month_start,
            models.Transaction.date <= month_end,
        )
    )
    spent = result.scalar()
    remaining = budget.monthly_limit - spent

    return schemas.BudgetStatusOut(
        budget=schemas.BudgetOut.model_validate(budget),
        spent=spent,
        remaining=remaining,
        exceeded=spent > budget.monthly_limit,
    )
