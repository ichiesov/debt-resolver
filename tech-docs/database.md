# Database

Supabase (PostgreSQL) via `supabase-py` async client. All queries are `await`ed — no sync I/O anywhere in the call stack.

---

## Tables

| Table | Description |
|---|---|
| `users` | One row per Telegram user (single-user bot, so always one row) |
| `loans` | Active and historical loans |
| `loan_payments` | Individual payment records per loan |
| `income_entries` | One-time and recurring income entries |
| `expense_entries` | One-time and recurring expense entries |
| `borrowed_entries` | P2P debts (lent / borrowed) |
| `p2p_repayments` | Partial repayments against borrowed/lent entries |
| `schema_migrations` | Applied migration tracking (managed by `scripts/migrate.py`) |

All tables include `user_id` (FK to `users.id`) and `deleted_at TIMESTAMP NULL` for soft deletes. Every query filters `deleted_at IS NULL`.

---

## Repository Pattern

One repository class per domain aggregate. Located in `app/db/repositories/`.

### Base

```python
class BaseRepository:
    def __init__(self, client: AsyncClient, user_id: uuid.UUID) -> None:
        self._client = client
        self._user_id = user_id
```

Every query automatically scopes to `user_id` — no cross-user data access is possible.

### UserRepository (special case)

`UserRepository(client)` takes no `user_id` — it *resolves* the `uuid.UUID` via `get_or_create(telegram_id)`. The resolved UUID is then passed to all other repositories at startup.

```python
user_id = await user_repo.get_or_create(telegram_id=bot_owner_id)
loan_repo = LoanRepository(client, user_id)
```

### Numeric Type Casting

Supabase returns PostgreSQL `numeric` columns as Python `str`. Repositories always cast on read:

```python
amount=Decimal(row["amount"])
```

And always use `str()` when writing:

```python
payload["amount"] = str(decimal_value)
```

Never use `float` for monetary values anywhere.

---

## Repositories Reference

### `LoanRepository`

| Method | Description |
|---|---|
| `get_all_active()` | `is_active=True AND deleted_at IS NULL` |
| `get_by_id(loan_id)` | Returns `None` if not found |
| `create(...)` | Inserts, returns mapped `Loan` |
| `update_balance(loan_id, new_balance)` | Called after each payment |
| `deactivate(loan_id)` | Sets `is_active=False` when balance reaches ₽0 |
| `soft_delete(loan_id)` | Sets `deleted_at` timestamp |

### `IncomeRepository` / `ExpenseRepository`

| Method | Description |
|---|---|
| `get_all_active()` | All non-deleted entries |
| `get_by_date_range(from, to)` | One-time: `entry_date IN [from, to]`; recurring: `entry_date ≤ to` (all active recurring entries since they were created) |
| `create(...)` | |
| `soft_delete(entry_id)` | |

The `get_by_date_range` method issues two queries (one-time and recurring) then deduplicates by `id`. This is necessary because recurring entries must be included regardless of when they were created, as long as their `recurrence_day` fires within the requested range.

### `BorrowedRepository`

| Method | Description |
|---|---|
| `get_all_active()` | `is_settled=False AND deleted_at IS NULL` |
| `get_by_direction(direction)` | `"lent"` or `"borrowed"` |
| `get_by_id(entry_id)` | Returns `None` if not found |
| `create(...)` | Sets `remaining_amount = original_amount` (no repayments yet) |
| `mark_settled(entry_id)` | Sets `is_settled=True, settled_at=now()` |
| `soft_delete(entry_id)` | |

`remaining_amount` is computed on every read: `original − SUM(p2p_repayments.amount)`. Not stored as a column; always recalculated from `p2p_repayments`.

### `UserRepository`

| Method | Description |
|---|---|
| `get_by_telegram_id(telegram_id)` | Returns `uuid.UUID` or `None` |
| `create(telegram_id, username)` | Inserts new user row |
| `get_or_create(telegram_id, username)` | Upsert pattern — called once at bot startup |

---

## Migrations

SQL migration files live in `app/db/migrations/`. Run them with:

```bash
uv run python scripts/migrate.py
```

The script:
1. Reads all `.sql` files ordered by filename (name them `001_initial.sql`, `002_add_term.sql`, etc.)
2. Checks `schema_migrations` table for already-applied filenames
3. Executes new migrations via the Supabase Management API
4. Records each applied migration

Requires `SUPABASE_ACCESS_TOKEN` in environment (separate from `SUPABASE_KEY`).

Dollar-quoted strings (`$$ ... $$`) and multi-statement files are supported.

---

## Supabase Client

`app/db/client.py` creates the async client once:

```python
client = create_client(settings.supabase_url, settings.supabase_key.get_secret_value())
```

Passed to all repositories at bot startup. Not a singleton — created fresh each run, but only once per process.
