"""
Apply SQL migrations to the Supabase project.

Tracks applied migrations in a `schema_migrations` table.
Already-applied migrations are skipped automatically.

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

CREATE_MIGRATIONS_TABLE = """
create table if not exists schema_migrations (
    filename text primary key,
    applied_at timestamptz not null default now()
);
"""

GET_APPLIED = "select filename from schema_migrations order by filename;"

MARK_APPLIED = "insert into schema_migrations (filename) values ('{filename}') on conflict do nothing;"


def get_project_ref(url: str) -> str:
    match = re.match(r"https://([^.]+)\.supabase\.co", url)
    if not match:
        sys.exit(f"Cannot parse project ref from SUPABASE_URL: {url}")
    return match.group(1)


def split_statements(sql: str) -> list[str]:
    statements: list[str] = []
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


ALREADY_EXISTS_ERRORS = (
    "already exists",
    "duplicate key value",
)


async def query(
    client: httpx.AsyncClient, project_ref: str, sql: str, ignore_exists: bool = False
) -> list[dict]:
    response = await client.post(
        f"https://api.supabase.com/v1/projects/{project_ref}/database/query",
        json={"query": sql},
    )
    if response.status_code not in (200, 201):
        if ignore_exists and any(e in response.text for e in ALREADY_EXISTS_ERRORS):
            return []
        raise RuntimeError(
            f"SQL failed ({response.status_code}): {response.text}\n\nSQL:\n{sql[:300]}"
        )
    return response.json() if response.text else []


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
        await query(client, project_ref, CREATE_MIGRATIONS_TABLE)

        rows = await query(client, project_ref, GET_APPLIED)
        applied = {row["filename"] for row in rows}

        pending = [f for f in migration_files if f.name not in applied]

        if not pending:
            print("✅ Все миграции уже применены.")
            return

        for path in pending:
            sql = path.read_text()
            statements = split_statements(sql)
            print(f"\n📄 {path.name} ({len(statements)} statements)")

            for i, stmt in enumerate(statements, 1):
                preview = stmt.splitlines()[0][:60]
                print(f"  [{i}/{len(statements)}] {preview}...")
                await query(client, project_ref, stmt, ignore_exists=True)

            await query(client, project_ref, MARK_APPLIED.format(filename=path.name))
            print(f"  ✅ {path.name} применён")

    print("\n✅ Готово!")


if __name__ == "__main__":
    asyncio.run(run_migrations())
