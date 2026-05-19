from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.domain.models import Loan, LoanType

from .base import BaseRepository

_TABLE = "loans"


class LoanRepository(BaseRepository):
    def _row_to_model(self, row: dict[str, Any]) -> Loan:
        return Loan(
            id=uuid.UUID(row["id"]),
            lender_name=row["lender_name"],
            principal_amount=Decimal(row["principal_amount"]),
            current_balance=Decimal(row["current_balance"]),
            annual_interest_rate=Decimal(row["annual_interest_rate"]),
            monthly_payment=Decimal(row["monthly_payment"]),
            payment_day=row["payment_day"],
            start_date=date.fromisoformat(row["start_date"]),
            end_date=date.fromisoformat(row["end_date"]) if row.get("end_date") else None,
            loan_type=LoanType(row["loan_type"]),
            is_active=row["is_active"],
            notes=row.get("notes"),
            term_months=row.get("term_months"),
        )

    async def get_all_active(self) -> list[Loan]:
        response = (
            await self._client.table(_TABLE)
            .select("*")
            .eq("user_id", self._user_id)
            .eq("is_active", True)
            .is_("deleted_at", "null")
            .execute()
        )
        return [self._row_to_model(r) for r in response.data]

    async def get_by_id(self, loan_id: uuid.UUID) -> Loan | None:
        response = (
            await self._client.table(_TABLE)
            .select("*")
            .eq("id", str(loan_id))
            .eq("user_id", self._user_id)
            .is_("deleted_at", "null")
            .execute()
        )
        if not response.data:
            return None
        return self._row_to_model(response.data[0])

    async def create(
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
        payload: dict[str, Any] = {
            "user_id": self._user_id,
            "lender_name": lender_name,
            "principal_amount": str(principal_amount),
            "current_balance": str(current_balance),
            "annual_interest_rate": str(annual_interest_rate),
            "monthly_payment": str(monthly_payment),
            "payment_day": payment_day,
            "start_date": start_date.isoformat(),
            "loan_type": loan_type,
            "end_date": end_date.isoformat() if end_date else None,
            "notes": notes,
            "term_months": term_months,
        }
        response = await self._client.table(_TABLE).insert(payload).execute()
        return self._row_to_model(response.data[0])

    async def update_balance(self, loan_id: uuid.UUID, new_balance: Decimal) -> None:
        await (
            self._client.table(_TABLE)
            .update({"current_balance": str(new_balance)})
            .eq("id", str(loan_id))
            .eq("user_id", self._user_id)
            .execute()
        )

    async def deactivate(self, loan_id: uuid.UUID) -> None:
        await (
            self._client.table(_TABLE)
            .update({"is_active": False})
            .eq("id", str(loan_id))
            .eq("user_id", self._user_id)
            .execute()
        )

    async def soft_delete(self, loan_id: uuid.UUID) -> None:
        await (
            self._client.table(_TABLE)
            .update({"deleted_at": datetime.utcnow().isoformat()})
            .eq("id", str(loan_id))
            .eq("user_id", self._user_id)
            .execute()
        )
