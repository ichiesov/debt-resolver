from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.optimization import rank_loans_by_avalanche
from tests.conftest import make_loan


def test_empty_loans():
    assert rank_loans_by_avalanche([]) == []


def test_single_loan():
    loan = make_loan(annual_interest_rate=Decimal("0.20"))
    recs = rank_loans_by_avalanche([loan])
    assert len(recs) == 1
    assert recs[0].rank == 1
    assert recs[0].loan is loan


def test_avalanche_ordering():
    low = make_loan(annual_interest_rate=Decimal("0.10"), lender_name="Low")
    high = make_loan(annual_interest_rate=Decimal("0.25"), lender_name="High")
    medium = make_loan(annual_interest_rate=Decimal("0.15"), lender_name="Medium")

    recs = rank_loans_by_avalanche([low, high, medium])
    assert [r.loan.lender_name for r in recs] == ["High", "Medium", "Low"]
    assert [r.rank for r in recs] == [1, 2, 3]


def test_inactive_loan_excluded():
    active = make_loan(annual_interest_rate=Decimal("0.20"), is_active=True)
    inactive = make_loan(annual_interest_rate=Decimal("0.30"), is_active=False)
    recs = rank_loans_by_avalanche([active, inactive])
    assert len(recs) == 1
    assert recs[0].loan is active


def test_zero_balance_loan_excluded():
    paid_off = make_loan(current_balance=Decimal("0"), annual_interest_rate=Decimal("0.20"))
    active = make_loan(current_balance=Decimal("50000"), annual_interest_rate=Decimal("0.15"))
    recs = rank_loans_by_avalanche([paid_off, active])
    assert len(recs) == 1
    assert recs[0].loan is active


def test_monthly_interest_calculation():
    loan = make_loan(
        current_balance=Decimal("120000"),
        annual_interest_rate=Decimal("0.12"),
    )
    recs = rank_loans_by_avalanche([loan])
    assert recs[0].monthly_interest_cost == Decimal("1200.00")


def test_months_to_payoff_reasonable():
    loan = make_loan(
        current_balance=Decimal("60000"),
        monthly_payment=Decimal("5000"),
        annual_interest_rate=Decimal("0.10"),
    )
    recs = rank_loans_by_avalanche([loan])
    assert 1 <= recs[0].months_to_payoff <= 24


def test_all_inactive_returns_empty():
    loans = [
        make_loan(is_active=False),
        make_loan(is_active=False),
    ]
    assert rank_loans_by_avalanche(loans) == []


def test_all_zero_balance_returns_empty():
    loans = [
        make_loan(current_balance=Decimal("0")),
        make_loan(current_balance=Decimal("0")),
    ]
    assert rank_loans_by_avalanche(loans) == []


def test_ranks_are_contiguous():
    loans = [
        make_loan(annual_interest_rate=Decimal("0.10"), lender_name="A"),
        make_loan(annual_interest_rate=Decimal("0.20"), lender_name="B"),
        make_loan(annual_interest_rate=Decimal("0.30"), lender_name="C"),
    ]
    recs = rank_loans_by_avalanche(loans)
    assert [r.rank for r in recs] == list(range(1, len(recs) + 1))


@pytest.mark.parametrize(
    "balance, rate, expected_monthly_interest",
    [
        (Decimal("12000"), Decimal("0.12"), Decimal("120.00")),
        (Decimal("100000"), Decimal("0.24"), Decimal("2000.00")),
        (Decimal("60000"), Decimal("0.10"), Decimal("500.00")),
        (Decimal("0"), Decimal("0.20"), Decimal("0.00")),
    ],
)
def test_monthly_interest_parametrize(balance, rate, expected_monthly_interest):
    loan = make_loan(current_balance=balance, annual_interest_rate=rate)
    if balance == Decimal("0"):
        recs = rank_loans_by_avalanche([loan])
        assert recs == []
        return
    recs = rank_loans_by_avalanche([loan])
    assert recs[0].monthly_interest_cost == expected_monthly_interest


def test_reason_contains_rate():
    loan = make_loan(annual_interest_rate=Decimal("0.15"))
    recs = rank_loans_by_avalanche([loan])
    assert "15.00%" in recs[0].reason


def test_interest_saved_is_non_negative():
    loans = [
        make_loan(annual_interest_rate=Decimal("0.25"), lender_name="High"),
        make_loan(annual_interest_rate=Decimal("0.10"), lender_name="Low"),
    ]
    recs = rank_loans_by_avalanche(loans)
    for rec in recs:
        assert rec.interest_saved_vs_minimum >= Decimal("0")


def test_payment_covers_only_interest_returns_large_months():
    loan = make_loan(
        current_balance=Decimal("100000"),
        annual_interest_rate=Decimal("0.12"),
        monthly_payment=Decimal("1000"),
    )
    recs = rank_loans_by_avalanche([loan])
    assert recs[0].months_to_payoff == 9999


@pytest.mark.parametrize(
    "input_order_rates, expected_order_rates",
    [
        (
            [Decimal("0.10"), Decimal("0.30"), Decimal("0.20")],
            [Decimal("0.30"), Decimal("0.20"), Decimal("0.10")],
        ),
        (
            [Decimal("0.05"), Decimal("0.25")],
            [Decimal("0.25"), Decimal("0.05")],
        ),
    ],
)
def test_avalanche_order_parametrize(input_order_rates, expected_order_rates):
    loans = [
        make_loan(annual_interest_rate=r, lender_name=str(r))
        for r in input_order_rates
    ]
    recs = rank_loans_by_avalanche(loans)
    assert [r.loan.annual_interest_rate for r in recs] == expected_order_rates
