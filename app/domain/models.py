from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum


class LoanType(StrEnum):
    MORTGAGE = "mortgage"
    CAR = "car"
    CONSUMER = "consumer"
    PERSONAL = "personal"


class Direction(StrEnum):
    LENT = "lent"
    BORROWED = "borrowed"


class PaymentType(StrEnum):
    SCHEDULED = "scheduled"
    EARLY = "early"
    PARTIAL = "partial"


@dataclass(frozen=True)
class Loan:
    id: uuid.UUID
    lender_name: str
    principal_amount: Decimal
    current_balance: Decimal
    annual_interest_rate: Decimal  # e.g. Decimal("0.1999") for 19.99%
    monthly_payment: Decimal
    payment_day: int               # day of month 1-31
    start_date: date
    end_date: date | None
    loan_type: LoanType
    is_active: bool
    notes: str | None
    term_months: int | None = None


@dataclass(frozen=True)
class IncomeEntry:
    id: uuid.UUID
    amount: Decimal
    description: str
    category: str
    entry_date: date
    is_recurring: bool
    recurrence_day: int | None


@dataclass(frozen=True)
class ExpenseEntry:
    id: uuid.UUID
    amount: Decimal
    description: str
    category: str
    entry_date: date
    is_recurring: bool
    recurrence_day: int | None


@dataclass(frozen=True)
class BorrowedEntry:
    id: uuid.UUID
    counterparty: str
    direction: Direction
    amount: Decimal
    remaining_amount: Decimal       # amount minus sum of repayments already recorded
    transaction_date: date
    expected_return_date: date | None
    is_settled: bool


@dataclass(frozen=True)
class LoanPayment:
    id: uuid.UUID
    loan_id: uuid.UUID
    amount: Decimal
    principal_part: Decimal | None
    interest_part: Decimal | None
    payment_date: date
    payment_type: PaymentType


@dataclass
class BalanceBreakdownItem:
    label: str
    amount: Decimal
    is_positive: bool               # True = adds to balance, False = subtracts


@dataclass
class DailyBalance:
    date: date
    opening_balance: Decimal
    total_income: Decimal
    total_expenses: Decimal
    total_loan_payments: Decimal
    net_p2p: Decimal                # positive = received > paid out
    closing_balance: Decimal
    breakdown: list[BalanceBreakdownItem] = field(default_factory=list)
