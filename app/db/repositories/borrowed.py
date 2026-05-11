from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.domain.models import BorrowedEntry, Direction

from .base import BaseRepository

_TABLE = "borrowed_entries"
_REPAYMENTS_TABLE = "p2p_repayments"


class BorrowedRepository(BaseRepository):
    async def _get_remaining(self, entry_id: uuid.UUID, original_amount: Decimal) -> Decimal:
        response = (
            await self._client.table(_REPAYMENTS_TABLE)
            .select("amount")
            .eq("entry_id", str(entry_id))
            .execute()
        )
        repaid = sum(Decimal(r["amount"]) for r in response.data)
        return original_amount - repaid

    def _row_to_model(self, row: dict[str, Any], remaining_amount: Decimal) -> BorrowedEntry:
        return BorrowedEntry(
            id=uuid.UUID(row["id"]),
            counterparty=row["counterparty"],
            direction=Direction(row["direction"]),
            amount=Decimal(row["amount"]),
            remaining_amount=remaining_amount,
            transaction_date=date.fromisoformat(row["transaction_date"]),
            expected_return_date=(
                date.fromisoformat(row["expected_return_date"])
                if row.get("expected_return_date")
                else None
            ),
            is_settled=row["is_settled"],
        )

    async def _rows_to_models(self, rows: list[dict[str, Any]]) -> list[BorrowedEntry]:
        entries: list[BorrowedEntry] = []
        for row in rows:
            entry_id = uuid.UUID(row["id"])
            original = Decimal(row["amount"])
            remaining = await self._get_remaining(entry_id, original)
            entries.append(self._row_to_model(row, remaining))
        return entries

    async def get_all_active(self) -> list[BorrowedEntry]:
        response = (
            await self._client.table(_TABLE)
            .select("*")
            .eq("user_id", self._user_id)
            .eq("is_settled", False)
            .is_("deleted_at", "null")
            .execute()
        )
        return await self._rows_to_models(response.data)

    async def get_by_direction(self, direction: str) -> list[BorrowedEntry]:
        response = (
            await self._client.table(_TABLE)
            .select("*")
            .eq("user_id", self._user_id)
            .eq("direction", direction)
            .is_("deleted_at", "null")
            .execute()
        )
        return await self._rows_to_models(response.data)

    async def get_by_id(self, entry_id: uuid.UUID) -> BorrowedEntry | None:
        response = (
            await self._client.table(_TABLE)
            .select("*")
            .eq("id", str(entry_id))
            .eq("user_id", self._user_id)
            .is_("deleted_at", "null")
            .execute()
        )
        if not response.data:
            return None
        row = response.data[0]
        original = Decimal(row["amount"])
        remaining = await self._get_remaining(entry_id, original)
        return self._row_to_model(row, remaining)

    async def create(
        self,
        counterparty: str,
        direction: str,
        amount: Decimal,
        transaction_date: date,
        description: str | None = None,
        expected_return_date: date | None = None,
    ) -> BorrowedEntry:
        payload: dict[str, Any] = {
            "user_id": self._user_id,
            "counterparty": counterparty,
            "direction": direction,
            "amount": str(amount),
            "transaction_date": transaction_date.isoformat(),
            "description": description,
            "expected_return_date": expected_return_date.isoformat() if expected_return_date else None,
        }
        response = await self._client.table(_TABLE).insert(payload).execute()
        row = response.data[0]
        return self._row_to_model(row, amount)

    async def mark_settled(self, entry_id: uuid.UUID) -> None:
        await (
            self._client.table(_TABLE)
            .update({"is_settled": True, "settled_at": datetime.utcnow().isoformat()})
            .eq("id", str(entry_id))
            .eq("user_id", self._user_id)
            .execute()
        )

    async def soft_delete(self, entry_id: uuid.UUID) -> None:
        await (
            self._client.table(_TABLE)
            .update({"deleted_at": datetime.utcnow().isoformat()})
            .eq("id", str(entry_id))
            .eq("user_id", self._user_id)
            .execute()
        )
