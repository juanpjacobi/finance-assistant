from datetime import date as date_, datetime as datetime_
from typing import Optional
from pydantic import BaseModel
import enum

class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    amount: float
    type: TransactionType
    date: Optional[date_] = None
    description: Optional[str] = None
    category_id: int

class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    type: Optional[TransactionType] = None
    date: Optional[date_] = None
    description: Optional[str] = None
    category_id: Optional[int] = None

class TransactionOut(BaseModel):
    id: int
    amount: float
    type: TransactionType
    date: date_
    description: Optional[str] = None
    category_id: int
    created_at: datetime_
    model_config = {"from_attributes": True}


class SummaryOut(BaseModel):
    date_from: date_
    date_to: date_
    total_income: float
    total_expenses: float
    balance: float


class Problem(BaseModel):
    type: str
    title: str
    status: int
    detail: Optional[str] = None


class BudgetCreate(BaseModel):
    category_id: int
    monthly_limit: float
    month: str

class BudgetOut(BaseModel):
    id: int
    category_id: int
    monthly_limit: float
    month: str
    created_at: datetime_
    model_config = {"from_attributes": True}

class BudgetStatusOut(BaseModel):
    budget: BudgetOut
    spent: float
    remaining: float
    exceeded: bool


class DocumentStatus(str, enum.Enum):
    processing = "processing"
    ready = "ready"
    error = "error"

class DocumentOut(BaseModel):
    id: int
    filename: str
    status: DocumentStatus
    uploaded_at: datetime_
    model_config = {"from_attributes": True}

class DocumentQuery(BaseModel):
    question: str

class DocumentQueryOut(BaseModel):
    question: str
    answer: str
