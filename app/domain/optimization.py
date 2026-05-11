from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import Loan


@dataclass(frozen=True)
class PayoffRecommendation:
    loan: Loan
    rank: int
    reason: str
    monthly_interest_cost: Decimal
    months_to_payoff: int
    interest_saved_vs_minimum: Decimal


def _monthly_interest(loan: Loan) -> Decimal:
    return (loan.current_balance * loan.annual_interest_rate / Decimal("12")).quantize(
        Decimal("0.01")
    )


def _months_to_payoff(loan: Loan) -> int:
    if loan.current_balance <= Decimal("0"):
        return 0
    principal_per_month = loan.monthly_payment - _monthly_interest(loan)
    if principal_per_month <= Decimal("0"):
        return 9999
    months = loan.current_balance / principal_per_month
    return int(months.to_integral_value()) + 1


def rank_loans_by_avalanche(loans: list[Loan]) -> list[PayoffRecommendation]:
    """Debt avalanche: rank active loans by annual_interest_rate descending.

    Paying the highest-rate loan first minimizes total interest paid and
    maximizes free cash flow once that loan is eliminated.
    """
    active = [loan for loan in loans if loan.is_active and loan.current_balance > Decimal("0")]
    sorted_loans = sorted(active, key=lambda loan: loan.annual_interest_rate, reverse=True)

    recommendations: list[PayoffRecommendation] = []
    for rank, loan in enumerate(sorted_loans, start=1):
        monthly_interest = _monthly_interest(loan)
        months = _months_to_payoff(loan)

        next_loan_months = (
            _months_to_payoff(sorted_loans[rank]) if rank < len(sorted_loans) else 0
        )
        interest_saved = monthly_interest * next_loan_months

        pct = loan.annual_interest_rate * Decimal("100")
        reason = f"Ставка {pct:.2f}% годовых — {monthly_interest:,.0f} ₽/мес. процентов"

        recommendations.append(
            PayoffRecommendation(
                loan=loan,
                rank=rank,
                reason=reason,
                monthly_interest_cost=monthly_interest,
                months_to_payoff=months,
                interest_saved_vs_minimum=interest_saved,
            )
        )

    return recommendations
