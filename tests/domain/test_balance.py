from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain.balance import calculate_balance_for_date, calculate_forecast
from app.domain.models import Direction
from tests.conftest import make_borrowed, make_expense, make_income, make_loan

TARGET = date(2025, 5, 1)
OPENING = Decimal("100000")


def _calc(
    target=TARGET,
    incomes=None,
    expenses=None,
    loans=None,
    borrowed=None,
    opening=OPENING,
):
    return calculate_balance_for_date(
        target,
        incomes or [],
        expenses or [],
        loans or [],
        borrowed or [],
        opening,
    )


def test_empty_inputs():
    result = _calc(opening=Decimal("100000"))
    assert result.closing_balance == Decimal("100000")
    assert result.total_income == Decimal("0")
    assert result.total_expenses == Decimal("0")
    assert result.total_loan_payments == Decimal("0")
    assert result.net_p2p == Decimal("0")


def test_one_time_income_on_date():
    income = make_income(amount=Decimal("50000"), entry_date=TARGET)
    result = _calc(incomes=[income], opening=Decimal("0"))
    assert result.total_income == Decimal("50000")
    assert result.closing_balance == Decimal("50000")


def test_one_time_income_not_on_date():
    income = make_income(amount=Decimal("50000"), entry_date=date(2025, 5, 2))
    result = _calc(incomes=[income], opening=Decimal("0"))
    assert result.total_income == Decimal("0")
    assert result.closing_balance == Decimal("0")


def test_recurring_income_fires_on_recurrence_day():
    income = make_income(
        amount=Decimal("50000"),
        entry_date=date(2025, 1, 1),
        is_recurring=True,
        recurrence_day=1,
    )
    result = _calc(target=date(2025, 5, 1), incomes=[income], opening=Decimal("0"))
    assert result.total_income == Decimal("50000")


def test_recurring_income_does_not_fire():
    income = make_income(
        amount=Decimal("50000"),
        entry_date=date(2025, 1, 1),
        is_recurring=True,
        recurrence_day=15,
    )
    result = _calc(target=date(2025, 5, 1), incomes=[income], opening=Decimal("0"))
    assert result.total_income == Decimal("0")


def test_recurring_income_before_start_date():
    income = make_income(
        amount=Decimal("50000"),
        entry_date=date(2025, 6, 1),
        is_recurring=True,
        recurrence_day=1,
    )
    result = _calc(target=date(2025, 5, 1), incomes=[income], opening=Decimal("0"))
    assert result.total_income == Decimal("0")


def test_recurring_income_clamps_feb():
    income = make_income(
        amount=Decimal("50000"),
        entry_date=date(2025, 1, 1),
        is_recurring=True,
        recurrence_day=31,
    )
    result = _calc(target=date(2025, 2, 28), incomes=[income], opening=Decimal("0"))
    assert result.total_income == Decimal("50000")


def test_expense_subtracted():
    expense = make_expense(amount=Decimal("10000"), entry_date=TARGET)
    result = _calc(expenses=[expense], opening=Decimal("50000"))
    assert result.total_expenses == Decimal("10000")
    assert result.closing_balance == Decimal("40000")


def test_loan_payment_on_payment_day():
    loan = make_loan(monthly_payment=Decimal("5000"), payment_day=15)
    result = _calc(target=date(2025, 5, 15), loans=[loan], opening=Decimal("20000"))
    assert result.total_loan_payments == Decimal("5000")
    assert result.closing_balance == Decimal("15000")


def test_loan_payment_not_on_other_day():
    loan = make_loan(monthly_payment=Decimal("5000"), payment_day=15)
    result = _calc(target=date(2025, 5, 14), loans=[loan], opening=Decimal("20000"))
    assert result.total_loan_payments == Decimal("0")
    assert result.closing_balance == Decimal("20000")


def test_inactive_loan_not_counted():
    loan = make_loan(monthly_payment=Decimal("5000"), payment_day=15, is_active=False)
    result = _calc(target=date(2025, 5, 15), loans=[loan], opening=Decimal("20000"))
    assert result.total_loan_payments == Decimal("0")
    assert result.closing_balance == Decimal("20000")


def test_borrowed_adds_to_balance():
    entry = make_borrowed(
        amount=Decimal("20000"),
        direction=Direction.BORROWED,
        transaction_date=TARGET,
    )
    result = _calc(borrowed=[entry], opening=Decimal("0"))
    assert result.net_p2p == Decimal("20000")
    assert result.closing_balance == Decimal("20000")


def test_lent_subtracts_from_balance():
    entry = make_borrowed(
        amount=Decimal("20000"),
        direction=Direction.LENT,
        transaction_date=TARGET,
    )
    result = _calc(borrowed=[entry], opening=Decimal("50000"))
    assert result.net_p2p == Decimal("-20000")
    assert result.closing_balance == Decimal("30000")


def test_complex_scenario():
    income = make_income(amount=Decimal("100000"), entry_date=TARGET)
    expense = make_expense(amount=Decimal("30000"), entry_date=TARGET)
    loan = make_loan(monthly_payment=Decimal("40000"), payment_day=TARGET.day)
    result = _calc(
        incomes=[income],
        expenses=[expense],
        loans=[loan],
        opening=Decimal("0"),
    )
    assert result.total_income == Decimal("100000")
    assert result.total_expenses == Decimal("30000")
    assert result.total_loan_payments == Decimal("40000")
    assert result.closing_balance == Decimal("30000")


@pytest.mark.parametrize(
    "direction, opening, expected_closing",
    [
        (Direction.BORROWED, Decimal("0"), Decimal("5000")),
        (Direction.LENT, Decimal("10000"), Decimal("5000")),
    ],
)
def test_p2p_direction_parametrize(direction, opening, expected_closing):
    entry = make_borrowed(
        amount=Decimal("5000"),
        direction=direction,
        transaction_date=TARGET,
    )
    result = _calc(borrowed=[entry], opening=opening)
    assert result.closing_balance == expected_closing


@pytest.mark.parametrize(
    "recurrence_day, target, should_fire",
    [
        (1, date(2025, 5, 1), True),
        (15, date(2025, 5, 1), False),
        (31, date(2025, 3, 31), True),
        (31, date(2025, 3, 30), False),
        (28, date(2025, 2, 28), True),
        (29, date(2025, 2, 28), True),
        (30, date(2025, 2, 28), True),
    ],
)
def test_recurring_clamp_parametrize(recurrence_day, target, should_fire):
    income = make_income(
        amount=Decimal("1000"),
        entry_date=date(2024, 1, 1),
        is_recurring=True,
        recurrence_day=recurrence_day,
    )
    result = _calc(target=target, incomes=[income], opening=Decimal("0"))
    assert (result.total_income == Decimal("1000")) == should_fire


def test_forecast_length():
    result = calculate_forecast(
        from_date=date(2025, 5, 1),
        days=7,
        incomes=[],
        expenses=[],
        loans=[],
        borrowed_entries=[],
        opening_balance=Decimal("0"),
    )
    assert len(result) == 7


def test_forecast_running_balance():
    income = make_income(
        amount=Decimal("1000"),
        entry_date=date(2025, 5, 1),
        is_recurring=False,
    )
    result = calculate_forecast(
        from_date=date(2025, 5, 1),
        days=3,
        incomes=[income],
        expenses=[],
        loans=[],
        borrowed_entries=[],
        opening_balance=Decimal("0"),
    )
    assert result[0].closing_balance == Decimal("1000")
    assert result[1].opening_balance == Decimal("1000")
    assert result[1].closing_balance == Decimal("1000")
    assert result[2].opening_balance == Decimal("1000")


def test_forecast_dates_are_sequential():
    result = calculate_forecast(
        from_date=date(2025, 5, 1),
        days=5,
        incomes=[],
        expenses=[],
        loans=[],
        borrowed_entries=[],
        opening_balance=Decimal("0"),
    )
    for i, daily in enumerate(result):
        from datetime import timedelta

        assert daily.date == date(2025, 5, 1) + timedelta(days=i)


def test_forecast_zero_days():
    result = calculate_forecast(
        from_date=date(2025, 5, 1),
        days=0,
        incomes=[],
        expenses=[],
        loans=[],
        borrowed_entries=[],
        opening_balance=Decimal("0"),
    )
    assert result == []


def test_breakdown_populated_on_income():
    income = make_income(amount=Decimal("50000"), entry_date=TARGET, description="Salary")
    result = _calc(incomes=[income], opening=Decimal("0"))
    assert any(item.label == "Salary" and item.amount == Decimal("50000") for item in result.breakdown)


def test_breakdown_populated_on_expense():
    expense = make_expense(amount=Decimal("10000"), entry_date=TARGET, description="Rent")
    result = _calc(expenses=[expense], opening=Decimal("0"))
    assert any(
        item.label == "Rent" and item.amount == Decimal("10000") and not item.is_positive
        for item in result.breakdown
    )


def test_opening_balance_preserved_in_result():
    result = _calc(opening=Decimal("77777"))
    assert result.opening_balance == Decimal("77777")


def test_borrowed_on_different_date_not_counted():
    entry = make_borrowed(
        amount=Decimal("20000"),
        direction=Direction.BORROWED,
        transaction_date=date(2025, 5, 2),
    )
    result = _calc(target=TARGET, borrowed=[entry], opening=Decimal("0"))
    assert result.net_p2p == Decimal("0")
    assert result.closing_balance == Decimal("0")


@pytest.mark.parametrize(
    "opening, income_amt, expense_amt, expected",
    [
        (Decimal("0"), Decimal("10000"), Decimal("3000"), Decimal("7000")),
        (Decimal("5000"), Decimal("0"), Decimal("5000"), Decimal("0")),
        (Decimal("1000"), Decimal("2000"), Decimal("500"), Decimal("2500")),
        (Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")),
    ],
)
def test_income_minus_expense_parametrize(opening, income_amt, expense_amt, expected):
    incomes = [make_income(amount=income_amt, entry_date=TARGET)] if income_amt else []
    expenses = [make_expense(amount=expense_amt, entry_date=TARGET)] if expense_amt else []
    result = _calc(incomes=incomes, expenses=expenses, opening=opening)
    assert result.closing_balance == expected
