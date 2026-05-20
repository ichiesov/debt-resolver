from __future__ import annotations

import uuid
from typing import Any

from supabase import AsyncClient

_TABLE = "users"


class UserRepository:
    # Unlike all other repositories, UserRepository takes no user_id — it resolves it via
    # get_or_create(telegram_id). The resolved UUID is then passed to every other repository.
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def get_by_telegram_id(self, telegram_id: int) -> uuid.UUID | None:
        response = (
            await self._client.table(_TABLE)
            .select("id")
            .eq("telegram_id", telegram_id)
            .execute()
        )
        if not response.data:
            return None
        return uuid.UUID(response.data[0]["id"])

    async def create(self, telegram_id: int, username: str | None = None) -> uuid.UUID:
        payload: dict[str, Any] = {
            "telegram_id": telegram_id,
            "username": username,
        }
        response = await self._client.table(_TABLE).insert(payload).execute()
        return uuid.UUID(response.data[0]["id"])

    async def get_or_create(self, telegram_id: int, username: str | None = None) -> uuid.UUID:
        existing = await self.get_by_telegram_id(telegram_id)
        if existing is not None:
            return existing
        return await self.create(telegram_id, username)
