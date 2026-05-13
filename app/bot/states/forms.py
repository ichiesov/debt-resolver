from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AddIncomeForm(StatesGroup):
    amount = State()
    description = State()
    entry_date = State()
    is_recurring = State()
    recurrence_day = State()


class AddExpenseForm(StatesGroup):
    amount = State()
    description = State()
    category = State()
    entry_date = State()
    is_recurring = State()
    recurrence_day = State()


class AddLoanForm(StatesGroup):
    lender_name = State()
    principal = State()
    current_balance = State()
    interest_rate = State()
    monthly_payment = State()
    payment_day = State()
    loan_type = State()
    confirm = State()


class AddBorrowedForm(StatesGroup):
    direction = State()
    counterparty = State()
    amount = State()
    transaction_date = State()
    expected_return_date = State()
