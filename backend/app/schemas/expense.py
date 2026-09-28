from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDatetime


class ExpenseCreateRequest(BaseModel):
    amount: float = Field(gt=0)
    description: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=64)
    spent_at: date | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    amount: float
    description: str
    category: str | None
    spent_at: date
    created_at: UtcDatetime


class ExpensesListOut(BaseModel):
    expenses: list[ExpenseOut]
    total: float
    by_category: dict[str, float]
