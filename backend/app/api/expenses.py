from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.expense import ExpenseCreateRequest, ExpenseOut, ExpensesListOut
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("", response_model=ExpenseOut, status_code=201)
async def create_expense(
    payload: ExpenseCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpenseOut:
    return await expense_service.add_expense(db, user, payload)


@router.get("", response_model=ExpensesListOut)
async def list_expenses(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    category: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpensesListOut:
    expenses = await expense_service.list_expenses(db, user, date_from, date_to, category)
    total, by_category = expense_service.totals(expenses)
    return ExpensesListOut(expenses=expenses, total=total, by_category=by_category)


@router.delete("/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await expense_service.delete_expense(db, user, expense_id)
