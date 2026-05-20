from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from app.db.repositories import (
    BorrowedRepository,
    ExpenseRepository,
    IncomeRepository,
    LoanRepository,
)
from app.domain.balance import calculate_balance_for_date, calculate_forecast
from app.domain.models import DailyBalance


class BalanceService:
    def __init__(
        self,
        income_repo: IncomeRepository,
        expense_repo: ExpenseRepository,
        loan_repo: LoanRepository,
        borrowed_repo: BorrowedRepository,
    ) -> None:
        self._income = income_repo
        self._expense = expense_repo
        self._loans = loan_repo
        self._borrowed = borrowed_repo

    async def get_balance_for_date(
        self, target_date: date, opening_balance: Decimal = Decimal("0")
    ) -> DailyBalance:
        # Fetch 3 years of history so recurring entries created before target_date are included.
        from_date = date(target_date.year - 3, 1, 1)

        incomes = await self._income.get_by_date_range(from_date, target_date)
        expenses = await self._expense.get_by_date_range(from_date, target_date)
        loans = await self._loans.get_all_active()
        borrowed = await self._borrowed.get_all_active()

        return calculate_balance_for_date(
            target_date, incomes, expenses, loans, borrowed, opening_balance
        )

    async def get_forecast(
        self, from_date: date, days: int = 30, opening_balance: Decimal = Decimal("0")
    ) -> list[DailyBalance]:
        to_date = from_date + timedelta(days=days)
        lookback = date(from_date.year - 3, 1, 1)

        incomes = await self._income.get_by_date_range(lookback, to_date)
        expenses = await self._expense.get_by_date_range(lookback, to_date)
        loans = await self._loans.get_all_active()
        borrowed = await self._borrowed.get_all_active()

        return calculate_forecast(from_date, days, incomes, expenses, loans, borrowed, opening_balance)
