from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.balance_service import BalanceService
from tests.conftest import make_borrowed, make_expense, make_income, make_loan
from app.domain.models import Direction


@pytest.fixture
def mock_repos():
    return {
        "income_repo": MagicMock(),
        "expense_repo": MagicMock(),
        "loan_repo": MagicMock(),
        "borrowed_repo": MagicMock(),
    }


@pytest.fixture
def balance_service(mock_repos):
    for repo in mock_repos.values():
        repo.get_by_date_range = AsyncMock(return_value=[])
        repo.get_all_active = AsyncMock(return_value=[])
    return BalanceService(**mock_repos)


@pytest.mark.asyncio
async def test_empty_returns_zero(balance_service):
    result = await balance_service.get_balance_for_date(date(2025, 5, 16))
    assert result.closing_balance == Decimal("0")


@pytest.mark.asyncio
async def test_income_added(mock_repos, balance_service):
    income = make_income(amount=Decimal("100000"), entry_date=date(2025, 5, 16))
    mock_repos["income_repo"].get_by_date_range = AsyncMock(return_value=[income])

    result = await balance_service.get_balance_for_date(date(2025, 5, 16))
    assert result.closing_balance == Decimal("100000")


@pytest.mark.asyncio
async def test_expense_subtracted(mock_repos, balance_service):
    income = make_income(amount=Decimal("100000"), entry_date=date(2025, 5, 16))
    expense = make_expense(amount=Decimal("30000"), entry_date=date(2025, 5, 16))
    mock_repos["income_repo"].get_by_date_range = AsyncMock(return_value=[income])
    mock_repos["expense_repo"].get_by_date_range = AsyncMock(return_value=[expense])

    result = await balance_service.get_balance_for_date(date(2025, 5, 16))
    assert result.closing_balance == Decimal("70000")


@pytest.mark.asyncio
async def test_forecast_length(balance_service):
    result = await balance_service.get_forecast(date(2025, 5, 16), days=7)
    assert len(result) == 7


@pytest.mark.asyncio
async def test_loan_payment_deducted(mock_repos, balance_service):
    income = make_income(amount=Decimal("100000"), entry_date=date(2025, 5, 16))
    loan = make_loan(monthly_payment=Decimal("40000"), payment_day=16)
    mock_repos["income_repo"].get_by_date_range = AsyncMock(return_value=[income])
    mock_repos["loan_repo"].get_all_active = AsyncMock(return_value=[loan])

    result = await balance_service.get_balance_for_date(date(2025, 5, 16))
    assert result.closing_balance == Decimal("60000")
    assert result.total_loan_payments == Decimal("40000")


@pytest.mark.asyncio
async def test_opening_balance_passed_through(mock_repos, balance_service):
    income = make_income(amount=Decimal("10000"), entry_date=date(2025, 5, 16))
    mock_repos["income_repo"].get_by_date_range = AsyncMock(return_value=[income])

    result = await balance_service.get_balance_for_date(
        date(2025, 5, 16), opening_balance=Decimal("50000")
    )
    assert result.opening_balance == Decimal("50000")
    assert result.closing_balance == Decimal("60000")


@pytest.mark.asyncio
async def test_borrowed_added_to_balance(mock_repos, balance_service):
    entry = make_borrowed(
        amount=Decimal("20000"),
        direction=Direction.BORROWED,
        transaction_date=date(2025, 5, 16),
    )
    mock_repos["borrowed_repo"].get_all_active = AsyncMock(return_value=[entry])

    result = await balance_service.get_balance_for_date(date(2025, 5, 16))
    assert result.net_p2p == Decimal("20000")
    assert result.closing_balance == Decimal("20000")


@pytest.mark.asyncio
async def test_lent_subtracted_from_balance(mock_repos, balance_service):
    entry = make_borrowed(
        amount=Decimal("15000"),
        direction=Direction.LENT,
        transaction_date=date(2025, 5, 16),
    )
    mock_repos["borrowed_repo"].get_all_active = AsyncMock(return_value=[entry])

    result = await balance_service.get_balance_for_date(
        date(2025, 5, 16), opening_balance=Decimal("50000")
    )
    assert result.net_p2p == Decimal("-15000")
    assert result.closing_balance == Decimal("35000")


@pytest.mark.asyncio
async def test_income_repo_called_with_date_range(mock_repos, balance_service):
    target = date(2025, 5, 16)
    await balance_service.get_balance_for_date(target)

    mock_repos["income_repo"].get_by_date_range.assert_awaited_once()
    call_args = mock_repos["income_repo"].get_by_date_range.call_args
    from_date, to_date = call_args.args
    assert to_date == target
    assert from_date < target


@pytest.mark.asyncio
async def test_loan_repo_get_all_active_called(mock_repos, balance_service):
    await balance_service.get_balance_for_date(date(2025, 5, 16))
    mock_repos["loan_repo"].get_all_active.assert_awaited_once()


@pytest.mark.asyncio
async def test_borrowed_repo_get_all_active_called(mock_repos, balance_service):
    await balance_service.get_balance_for_date(date(2025, 5, 16))
    mock_repos["borrowed_repo"].get_all_active.assert_awaited_once()


@pytest.mark.asyncio
async def test_forecast_zero_days(balance_service):
    result = await balance_service.get_forecast(date(2025, 5, 16), days=0)
    assert result == []


@pytest.mark.asyncio
async def test_forecast_opening_balance_propagates(mock_repos, balance_service):
    income = make_income(
        amount=Decimal("1000"),
        entry_date=date(2025, 5, 1),
        is_recurring=False,
    )
    mock_repos["income_repo"].get_by_date_range = AsyncMock(return_value=[income])

    result = await balance_service.get_forecast(
        date(2025, 5, 1), days=2, opening_balance=Decimal("5000")
    )
    assert result[0].opening_balance == Decimal("5000")
    assert result[1].opening_balance == result[0].closing_balance


@pytest.mark.asyncio
async def test_multiple_loans_all_deducted(mock_repos, balance_service):
    loan_a = make_loan(monthly_payment=Decimal("10000"), payment_day=16, lender_name="A")
    loan_b = make_loan(monthly_payment=Decimal("5000"), payment_day=16, lender_name="B")
    mock_repos["loan_repo"].get_all_active = AsyncMock(return_value=[loan_a, loan_b])

    result = await balance_service.get_balance_for_date(
        date(2025, 5, 16), opening_balance=Decimal("30000")
    )
    assert result.total_loan_payments == Decimal("15000")
    assert result.closing_balance == Decimal("15000")


@pytest.mark.asyncio
async def test_multiple_expenses_summed(mock_repos, balance_service):
    e1 = make_expense(amount=Decimal("3000"), entry_date=date(2025, 5, 16), description="Rent")
    e2 = make_expense(amount=Decimal("2000"), entry_date=date(2025, 5, 16), description="Food")
    mock_repos["expense_repo"].get_by_date_range = AsyncMock(return_value=[e1, e2])

    result = await balance_service.get_balance_for_date(
        date(2025, 5, 16), opening_balance=Decimal("10000")
    )
    assert result.total_expenses == Decimal("5000")
    assert result.closing_balance == Decimal("5000")


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [1, 7, 14, 30])
async def test_forecast_various_lengths(days, balance_service):
    result = await balance_service.get_forecast(date(2025, 5, 1), days=days)
    assert len(result) == days


@pytest.mark.asyncio
async def test_inactive_loan_not_counted_in_service(mock_repos, balance_service):
    loan = make_loan(monthly_payment=Decimal("20000"), payment_day=16, is_active=False)
    mock_repos["loan_repo"].get_all_active = AsyncMock(return_value=[loan])

    result = await balance_service.get_balance_for_date(
        date(2025, 5, 16), opening_balance=Decimal("10000")
    )
    assert result.total_loan_payments == Decimal("0")
    assert result.closing_balance == Decimal("10000")
