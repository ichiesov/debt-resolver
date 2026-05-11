from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.models import LoanPayment, PaymentType

from .base import BaseRepository

_TABLE = "loan_payments"


class LoanPaymentRepository(BaseRepository):
    def _row_to_model(self, row: dict[str, Any]) -> LoanPayment:
        return LoanPayment(
            id=uuid.UUID(row["id"]),
            loan_id=uuid.UUID(row["loan_id"]),
            amount=Decimal(row["amount"]),
            principal_part=Decimal(row["principal_part"]) if row.get("principal_part") is not None else None,
            interest_part=Decimal(row["interest_part"]) if row.get("interest_part") is not None else None,
            payment_date=date.fromisoformat(row["payment_date"]),
            payment_type=PaymentType(row["payment_type"]),
        )

    async def get_by_loan(self, loan_id: uuid.UUID) -> list[LoanPayment]:
        response = (
            await self._client.table(_TABLE)
            .select("*")
            .eq("loan_id", str(loan_id))
            .eq("user_id", self._user_id)
            .execute()
        )
        return [self._row_to_model(r) for r in response.data]

    async def create(
        self,
        loan_id: uuid.UUID,
        amount: Decimal,
        payment_date: date,
        payment_type: str = "scheduled",
        principal_part: Decimal | None = None,
        interest_part: Decimal | None = None,
    ) -> LoanPayment:
        payload: dict[str, Any] = {
            "user_id": self._user_id,
            "loan_id": str(loan_id),
            "amount": str(amount),
            "payment_date": payment_date.isoformat(),
            "payment_type": payment_type,
            "principal_part": str(principal_part) if principal_part is not None else None,
            "interest_part": str(interest_part) if interest_part is not None else None,
        }
        response = await self._client.table(_TABLE).insert(payload).execute()
        return self._row_to_model(response.data[0])
