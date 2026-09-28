from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Expense, User
from app.errors import NotFound
from app.schemas.expense import ExpenseCreateRequest

UNCATEGORIZED = "Sonstiges"


async def add_expense(db: AsyncSession, user: User, payload: ExpenseCreateRequest) -> Expense:
    expense = Expense(
        user_id=user.id,
        amount=payload.amount,
        description=payload.description.strip(),
        category=payload.category.strip() if payload.category else None,
        spent_at=payload.spent_at or date.today(),
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return expense


async def list_expenses(
    db: AsyncSession,
    user: User,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
) -> list[Expense]:
    query = select(Expense).where(Expense.user_id == user.id)
    if date_from is not None:
        query = query.where(Expense.spent_at >= date_from)
    if date_to is not None:
        query = query.where(Expense.spent_at <= date_to)
    if category is not None:
        query = query.where(Expense.category == category)
    query = query.order_by(Expense.spent_at.desc(), Expense.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


def totals(expenses: list[Expense]) -> tuple[float, dict[str, float]]:
    total = sum(e.amount for e in expenses)
    by_category: dict[str, float] = {}
    for expense in expenses:
        key = expense.category or UNCATEGORIZED
        by_category[key] = by_category.get(key, 0.0) + expense.amount
    return total, by_category


async def delete_expense(db: AsyncSession, user: User, expense_id: str) -> None:
    expense = await db.get(Expense, expense_id)
    if expense is None or expense.user_id != user.id:
        raise NotFound("Ausgabe nicht gefunden.")
    await db.delete(expense)
    await db.commit()
