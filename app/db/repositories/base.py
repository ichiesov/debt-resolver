from __future__ import annotations

import uuid

from supabase import AsyncClient


class BaseRepository:
    def __init__(self, client: AsyncClient, user_id: uuid.UUID) -> None:
        self._client = client
        self._user_id = str(user_id)
