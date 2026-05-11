from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.domain.models import IncomeEntry

from .base import BaseRepository

_TABLE = "income_entries"


class IncomeRepository(BaseRepository):
    def _row_to_model(self, row: dict[str, Any]) -> IncomeEntry:
        return IncomeEntry(
            id=uuid.UUID(row["id"]),
            amount=Decimal(row["amount"]),
            description=row["description"],
            category=row["category"],
            entry_date=date.fromisoformat(row["entry_date"]),
            is_recurring=row["is_recurring"],
            recurrence_day=row["recurrence_day"],
        )

    async def get_all_active(self) -> list[IncomeEntry]:
        response = (
            await self._client.table(_TABLE)
            .select("*")
            .eq("user_id", self._user_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return [self._row_to_model(r) for r in response.data]

    async def get_by_date_range(self, from_date: date, to_date: date) -> list[IncomeEntry]:
        one_time_resp = (
            await self._client.table(_TABLE)
            .select("*")
            .eq("user_id", self._user_id)
            .eq("is_recurring", False)
            .gte("entry_date", from_date.isoformat())
            .lte("entry_date", to_date.isoformat())
            .is_("deleted_at", "null")
            .execute()
        )

        recurring_resp = (
            await self._client.table(_TABLE)
            .select("*")
            .eq("user_id", self._user_id)
            .eq("is_recurring", True)
            .lte("entry_date", to_date.isoformat())
            .is_("deleted_at", "null")
            .execute()
        )

        seen: set[str] = set()
        entries: list[IncomeEntry] = []
        for row in one_time_resp.data + recurring_resp.data:
            if row["id"] not in seen:
                seen.add(row["id"])
                entries.append(self._row_to_model(row))
        return entries

    async def create(
        self,
        amount: Decimal,
        description: str,
        category: str,
        entry_date: date,
        is_recurring: bool = False,
        recurrence_day: int | None = None,
    ) -> IncomeEntry:
        payload: dict[str, Any] = {
            "user_id": self._user_id,
            "amount": str(amount),
            "description": description,
            "category": category,
            "entry_date": entry_date.isoformat(),
            "is_recurring": is_recurring,
            "recurrence_day": recurrence_day,
        }
        response = await self._client.table(_TABLE).insert(payload).execute()
        return self._row_to_model(response.data[0])

    async def soft_delete(self, entry_id: uuid.UUID) -> None:
        await (
            self._client.table(_TABLE)
            .update({"deleted_at": datetime.utcnow().isoformat()})
            .eq("id", str(entry_id))
            .eq("user_id", self._user_id)
            .execute()
        )
