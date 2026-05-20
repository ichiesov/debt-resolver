from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.db.repositories import BorrowedRepository, ExpenseRepository, IncomeRepository
from app.domain.models import BorrowedEntry, ExpenseEntry, IncomeEntry


class TransactionService:
    def __init__(
        self,
        income_repo: IncomeRepository,
        expense_repo: ExpenseRepository,
        borrowed_repo: BorrowedRepository,
    ) -> None:
        self._income = income_repo
        self._expense = expense_repo
        self._borrowed = borrowed_repo

    async def add_income(
        self,
        amount: Decimal,
        description: str,
        category: str,
        entry_date: date,
        is_recurring: bool = False,
        recurrence_day: int | None = None,
    ) -> IncomeEntry:
        return await self._income.create(
            amount=amount,
            description=description,
            category=category,
            entry_date=entry_date,
            is_recurring=is_recurring,
            recurrence_day=recurrence_day,
        )

    async def add_expense(
        self,
        amount: Decimal,
        description: str,
        category: str,
        entry_date: date,
        is_recurring: bool = False,
        recurrence_day: int | None = None,
    ) -> ExpenseEntry:
        return await self._expense.create(
            amount=amount,
            description=description,
            category=category,
            entry_date=entry_date,
            is_recurring=is_recurring,
            recurrence_day=recurrence_day,
        )

    async def get_recent_incomes(self, from_date: date, to_date: date) -> list[IncomeEntry]:
        return await self._income.get_by_date_range(from_date, to_date)

    async def get_recent_expenses(self, from_date: date, to_date: date) -> list[ExpenseEntry]:
        return await self._expense.get_by_date_range(from_date, to_date)

    async def delete_income(self, entry_id: uuid.UUID) -> None:
        """Soft-delete: sets deleted_at, entry is excluded from all future queries."""
        await self._income.soft_delete(entry_id)

    async def delete_expense(self, entry_id: uuid.UUID) -> None:
        """Soft-delete: sets deleted_at, entry is excluded from all future queries."""
        await self._expense.soft_delete(entry_id)

    async def add_borrowed(
        self,
        counterparty: str,
        direction: str,
        amount: Decimal,
        transaction_date: date,
        description: str | None = None,
        expected_return_date: date | None = None,
    ) -> BorrowedEntry:
        return await self._borrowed.create(
            counterparty=counterparty,
            direction=direction,
            amount=amount,
            transaction_date=transaction_date,
            description=description,
            expected_return_date=expected_return_date,
        )

    async def get_lent(self) -> list[BorrowedEntry]:
        return await self._borrowed.get_by_direction("lent")

    async def get_borrowed(self) -> list[BorrowedEntry]:
        return await self._borrowed.get_by_direction("borrowed")

    async def mark_settled(self, entry_id: uuid.UUID) -> None:
        await self._borrowed.mark_settled(entry_id)
