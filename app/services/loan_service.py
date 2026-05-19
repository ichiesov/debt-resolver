from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.db.repositories import LoanPaymentRepository, LoanRepository
from app.domain.exceptions import LoanNotFoundError
from app.domain.models import Loan, LoanPayment


class LoanService:
    def __init__(self, loan_repo: LoanRepository, payment_repo: LoanPaymentRepository) -> None:
        self._loans = loan_repo
        self._payments = payment_repo

    async def get_all_active(self) -> list[Loan]:
        return await self._loans.get_all_active()

    async def get_by_id(self, loan_id: uuid.UUID) -> Loan:
        loan = await self._loans.get_by_id(loan_id)
        if loan is None:
            raise LoanNotFoundError(f"Loan {loan_id} not found")
        return loan

    async def add_loan(
        self,
        lender_name: str,
        principal_amount: Decimal,
        current_balance: Decimal,
        annual_interest_rate: Decimal,
        monthly_payment: Decimal,
        payment_day: int,
        start_date: date,
        loan_type: str,
        end_date: date | None = None,
        notes: str | None = None,
        term_months: int | None = None,
    ) -> Loan:
        return await self._loans.create(
            lender_name=lender_name,
            principal_amount=principal_amount,
            current_balance=current_balance,
            annual_interest_rate=annual_interest_rate,
            monthly_payment=monthly_payment,
            payment_day=payment_day,
            start_date=start_date,
            loan_type=loan_type,
            end_date=end_date,
            notes=notes,
            term_months=term_months,
        )

    async def record_payment(
        self,
        loan_id: uuid.UUID,
        amount: Decimal,
        payment_date: date,
        payment_type: str = "scheduled",
        principal_part: Decimal | None = None,
        interest_part: Decimal | None = None,
    ) -> LoanPayment:
        loan = await self.get_by_id(loan_id)
        payment = await self._payments.create(
            loan_id=loan_id,
            amount=amount,
            payment_date=payment_date,
            payment_type=payment_type,
            principal_part=principal_part,
            interest_part=interest_part,
        )
        new_balance = max(Decimal("0"), loan.current_balance - (principal_part or amount))
        await self._loans.update_balance(loan_id, new_balance)
        if new_balance == Decimal("0"):
            await self._loans.deactivate(loan_id)
        return payment

    async def get_payments(self, loan_id: uuid.UUID) -> list[LoanPayment]:
        return await self._payments.get_by_loan(loan_id)
