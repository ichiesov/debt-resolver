from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from .models import (
    BalanceBreakdownItem,
    BorrowedEntry,
    DailyBalance,
    Direction,
    ExpenseEntry,
    IncomeEntry,
    Loan,
)


def _fires_on_date(target: date, recurrence_day: int, since: date) -> bool:
    """True if a recurring entry fires on `target` given its recurrence_day.
    Clamps to the last day of the month when recurrence_day > month length.
    Returns False if target is before since."""
    if target < since:
        return False
    last_day = monthrange(target.year, target.month)[1]
    effective_day = min(recurrence_day, last_day)
    return target.day == effective_day


def _loan_fires_on_date(target: date, payment_day: int, loan_start: date) -> bool:
    """True if a scheduled loan payment falls on target (same logic as recurring entries)."""
    return _fires_on_date(target, payment_day, loan_start)


def calculate_balance_for_date(
    target_date: date,
    incomes: list[IncomeEntry],
    expenses: list[ExpenseEntry],
    loans: list[Loan],
    borrowed_entries: list[BorrowedEntry],
    opening_balance: Decimal,
) -> DailyBalance:
    """Calculate the closing balance for a single date.

    All lists must be pre-fetched by the caller (service layer).
    - One-time entries: included only if entry_date == target_date
    - Recurring entries: included if their recurrence_day fires on target_date
    - Loans: monthly payment deducted on payment_day (if loan is active)
    - BorrowedEntry direction='borrowed' adds money; direction='lent' subtracts
    """
    breakdown: list[BalanceBreakdownItem] = []
    total_income = Decimal("0")
    total_expenses = Decimal("0")
    total_loan_payments = Decimal("0")
    net_p2p = Decimal("0")

    for entry in incomes:
        if entry.is_recurring:
            if entry.recurrence_day is None:
                continue
            if not _fires_on_date(target_date, entry.recurrence_day, entry.entry_date):
                continue
        elif entry.entry_date != target_date:
            continue
        total_income += entry.amount
        breakdown.append(BalanceBreakdownItem(entry.description, entry.amount, True))

    for entry in expenses:
        if entry.is_recurring:
            if entry.recurrence_day is None:
                continue
            if not _fires_on_date(target_date, entry.recurrence_day, entry.entry_date):
                continue
        elif entry.entry_date != target_date:
            continue
        total_expenses += entry.amount
        breakdown.append(BalanceBreakdownItem(entry.description, entry.amount, False))

    for loan in loans:
        if not loan.is_active:
            continue
        if _loan_fires_on_date(target_date, loan.payment_day, loan.start_date):
            total_loan_payments += loan.monthly_payment
            breakdown.append(
                BalanceBreakdownItem(f"Платёж: {loan.lender_name}", loan.monthly_payment, False)
            )

    for entry in borrowed_entries:
        if entry.transaction_date != target_date:
            continue
        if entry.direction == Direction.BORROWED:
            net_p2p += entry.amount
            breakdown.append(
                BalanceBreakdownItem(f"Занял у {entry.counterparty}", entry.amount, True)
            )
        else:
            net_p2p -= entry.amount
            breakdown.append(
                BalanceBreakdownItem(f"Одолжил {entry.counterparty}", entry.amount, False)
            )

    closing_balance = (
        opening_balance + total_income - total_expenses - total_loan_payments + net_p2p
    )

    return DailyBalance(
        date=target_date,
        opening_balance=opening_balance,
        total_income=total_income,
        total_expenses=total_expenses,
        total_loan_payments=total_loan_payments,
        net_p2p=net_p2p,
        closing_balance=closing_balance,
        breakdown=breakdown,
    )


def calculate_forecast(
    from_date: date,
    days: int,
    incomes: list[IncomeEntry],
    expenses: list[ExpenseEntry],
    loans: list[Loan],
    borrowed_entries: list[BorrowedEntry],
    opening_balance: Decimal,
) -> list[DailyBalance]:
    """Return rolling daily balance for `days` days starting from from_date."""
    from datetime import timedelta

    result: list[DailyBalance] = []
    current_balance = opening_balance

    for i in range(days):
        day = from_date + timedelta(days=i)
        daily = calculate_balance_for_date(
            day, incomes, expenses, loans, borrowed_entries, current_balance
        )
        result.append(daily)
        current_balance = daily.closing_balance

    return result
