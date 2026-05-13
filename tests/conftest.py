from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.domain.models import (
    BorrowedEntry,
    Direction,
    ExpenseEntry,
    IncomeEntry,
    Loan,
    LoanType,
)


def make_loan(
    current_balance: Decimal = Decimal("100000"),
    annual_interest_rate: Decimal = Decimal("0.15"),
    monthly_payment: Decimal = Decimal("5000"),
    payment_day: int = 15,
    is_active: bool = True,
    lender_name: str = "Test Bank",
) -> Loan:
    return Loan(
        id=uuid.uuid4(),
        lender_name=lender_name,
        principal_amount=Decimal("200000"),
        current_balance=current_balance,
        annual_interest_rate=annual_interest_rate,
        monthly_payment=monthly_payment,
        payment_day=payment_day,
        start_date=date(2024, 1, 1),
        end_date=None,
        loan_type=LoanType.CONSUMER,
        is_active=is_active,
        notes=None,
    )


def make_income(
    amount: Decimal = Decimal("50000"),
    entry_date: date = date(2025, 5, 1),
    is_recurring: bool = False,
    recurrence_day: int | None = None,
    description: str = "Зарплата",
) -> IncomeEntry:
    return IncomeEntry(
        id=uuid.uuid4(),
        amount=amount,
        description=description,
        category="salary",
        entry_date=entry_date,
        is_recurring=is_recurring,
        recurrence_day=recurrence_day,
    )


def make_expense(
    amount: Decimal = Decimal("10000"),
    entry_date: date = date(2025, 5, 1),
    is_recurring: bool = False,
    recurrence_day: int | None = None,
    description: str = "Продукты",
) -> ExpenseEntry:
    return ExpenseEntry(
        id=uuid.uuid4(),
        amount=amount,
        description=description,
        category="food",
        entry_date=entry_date,
        is_recurring=is_recurring,
        recurrence_day=recurrence_day,
    )


def make_borrowed(
    amount: Decimal = Decimal("20000"),
    direction: Direction = Direction.BORROWED,
    transaction_date: date = date(2025, 5, 1),
    counterparty: str = "Иван",
) -> BorrowedEntry:
    return BorrowedEntry(
        id=uuid.uuid4(),
        counterparty=counterparty,
        direction=direction,
        amount=amount,
        remaining_amount=amount,
        transaction_date=transaction_date,
        expected_return_date=None,
        is_settled=False,
    )
