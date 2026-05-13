from __future__ import annotations

from aiogram import types
from aiogram.filters import BaseFilter

from app.config import settings


class IsOwnerFilter(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user is not None and message.from_user.id == settings.telegram_owner_id
