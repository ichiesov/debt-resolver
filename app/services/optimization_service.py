from __future__ import annotations

from app.db.repositories import LoanRepository
from app.domain.optimization import PayoffRecommendation, rank_loans_by_avalanche


class OptimizationService:
    def __init__(self, loan_repo: LoanRepository) -> None:
        self._loans = loan_repo

    async def get_recommendations(self) -> list[PayoffRecommendation]:
        loans = await self._loans.get_all_active()
        return rank_loans_by_avalanche(loans)
