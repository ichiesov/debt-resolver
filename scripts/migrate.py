"""
Apply SQL migrations to the Supabase project.

Requires SUPABASE_ACCESS_TOKEN in .env — a Personal Access Token from:
  https://supabase.com/dashboard/account/tokens

Usage:
    uv run python scripts/migrate.py
"""

import asyncio
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN", "")

MIGRATIONS_DIR = Path(__file__).parent.parent / "app" / "db" / "migrations"


def get_project_ref(url: str) -> str:
    match = re.match(r"https://([^.]+)\.supabase\.co", url)
    if not match:
        sys.exit(f"Cannot parse project ref from SUPABASE_URL: {url}")
    return match.group(1)


def split_statements(sql: str) -> list[str]:
    """Split SQL into individual statements, skipping empty ones."""
    statements = []
    current: list[str] = []
    in_dollar_quote = False

    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        if "$$" in line:
            in_dollar_quote = not in_dollar_quote
        current.append(line)
        if not in_dollar_quote and stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            current = []

    return statements


async def execute_sql(client: httpx.AsyncClient, project_ref: str, sql: str) -> None:
    response = await client.post(
        f"https://api.supabase.com/v1/projects/{project_ref}/database/query",
        json={"query": sql},
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"SQL failed ({response.status_code}): {response.text}\n\nSQL:\n{sql[:300]}")


async def run_migrations() -> None:
    if not SUPABASE_ACCESS_TOKEN:
        print(
            "\n❌  SUPABASE_ACCESS_TOKEN не задан.\n\n"
            "  Получить токен:\n"
            "  1. Открой https://supabase.com/dashboard/account/tokens\n"
            "  2. Нажми «Generate new token»\n"
            "  3. Добавь в .env:\n"
            "     SUPABASE_ACCESS_TOKEN=sbp_xxxxxxxxxxxxxxxx\n"
        )
        sys.exit(1)

    project_ref = get_project_ref(SUPABASE_URL)
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not migration_files:
        print("Миграций не найдено.")
        return

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {SUPABASE_ACCESS_TOKEN}"},
        timeout=30,
    ) as client:
        for path in migration_files:
            sql = path.read_text()
            statements = split_statements(sql)
            print(f"\n📄 {path.name} ({len(statements)} statements)")

            for i, stmt in enumerate(statements, 1):
                preview = stmt.splitlines()[0][:60]
                print(f"  [{i}/{len(statements)}] {preview}...")
                await execute_sql(client, project_ref, stmt)

            print(f"  ✅ {path.name} применён")

    print("\n✅ Все миграции применены успешно!")


if __name__ == "__main__":
    asyncio.run(run_migrations())
