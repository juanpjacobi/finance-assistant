from datetime import date as date_
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from api.database import get_db
from api import models, schemas

router = APIRouter(prefix="/transactions", tags=["transactions"])

async def get_transaction_or_404(id: int, db: AsyncSession) -> models.Transaction:
    result = await db.execute(
        select(models.Transaction).where(models.Transaction.id == id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://api.financeassistant.dev/errors/not-found",
                "title": "Resource not found",
                "status": 404,
                "detail": f"Transaction with id {id} does not exist",
            },
        )
    return transaction

@router.get("/summary", response_model=schemas.SummaryOut)
async def get_summary(
    date_from: date_ = Query(...),
    date_to: date_ = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            func.coalesce(
                func.sum(models.Transaction.amount).filter(
                    models.Transaction.type == models.TransactionType.income
                ), 0.0
            ),
            func.coalesce(
                func.sum(models.Transaction.amount).filter(
                    models.Transaction.type == models.TransactionType.expense
                ), 0.0
            ),
        ).where(
            models.Transaction.date >= date_from,
            models.Transaction.date <= date_to,
        )
    )
    total_income, total_expenses = result.one()
    return schemas.SummaryOut(
        date_from=date_from,
        date_to=date_to,
        total_income=total_income,
        total_expenses=total_expenses,
        balance=total_income - total_expenses,
    )

@router.get("", response_model=list[schemas.TransactionOut])
async def list_transactions(
    type: schemas.TransactionType | None = Query(None),
    category_id: int | None = Query(None),
    date_from: date_ | None = Query(None),
    date_to: date_ | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(models.Transaction)
    if type:
        query = query.where(models.Transaction.type == models.TransactionType(type.value))
    if category_id:
        query = query.where(models.Transaction.category_id == category_id)
    if date_from:
        query = query.where(models.Transaction.date >= date_from)
    if date_to:
        query = query.where(models.Transaction.date <= date_to)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("", response_model=schemas.TransactionOut, status_code=201)
async def create_transaction(
    body: schemas.TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
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
    data = body.model_dump()
    if data["date"] is None:
        data["date"] = date_.today()
    transaction = models.Transaction(**data)
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    return transaction

@router.get("/{id}", response_model=schemas.TransactionOut)
async def get_transaction(id: int, db: AsyncSession = Depends(get_db)):
    return await get_transaction_or_404(id, db)

@router.put("/{id}", response_model=schemas.TransactionOut)
async def update_transaction(
    id: int,
    body: schemas.TransactionUpdate,
    db: AsyncSession = Depends(get_db),
):
    transaction = await get_transaction_or_404(id, db)
    if body.category_id:
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
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(transaction, field, value)
    await db.commit()
    await db.refresh(transaction)
    return transaction

@router.delete("/{id}", status_code=204)
async def delete_transaction(id: int, db: AsyncSession = Depends(get_db)):
    transaction = await get_transaction_or_404(id, db)
    await db.delete(transaction)
    await db.commit()