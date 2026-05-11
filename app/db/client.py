from __future__ import annotations

from functools import lru_cache

from supabase import AsyncClient, acreate_client

from app.config import settings


@lru_cache(maxsize=1)
def _get_supabase_url() -> str:
    return settings.supabase_url


@lru_cache(maxsize=1)
def _get_supabase_key() -> str:
    return settings.supabase_key.get_secret_value()


async def get_client() -> AsyncClient:
    return await acreate_client(_get_supabase_url(), _get_supabase_key())
