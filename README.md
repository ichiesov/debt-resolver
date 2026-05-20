# debt-resolver

Personal finance tracker for managing debts, loans, and cash flow — delivered as a single-user Telegram bot.

The bot interface is in Russian. All monetary amounts are in RUB (₽).

---

## Features

| Feature | Commands | Description |
|---|---|---|
| **Balance** | `/balance [ДД.ММ]` | Daily balance for any date — income, expenses, loan payments, P2P |
| **Forecast** | `/forecast [N]` | Rolling N-day (default 30, max 90) cash flow forecast |
| **Loans** | `/loans` | All active loans sorted by rate (descending) with months left |
| **Record payment** | `/pay_loan` | Record a loan payment (updates balance, auto-closes at ₽0) |
| **Add loan** | `/add_loan` | Multi-step form: name, principal, balance, rate, payment, term, day, type |
| **Income** | `/add_income` · `/incomes` | One-time or monthly-recurring income |
| **Expenses** | `/add_expense` · `/expenses` | One-time or monthly-recurring expense with category |
| **P2P debts** | `/lent` · `/borrowed` · `/add_debt` | Track money lent to or borrowed from people |
| **Optimization** | `/optimize` | Debt avalanche ranking — highest rate first |

---

## Architecture at a Glance

```
main.py
└── app/
    ├── domain/          # Pure functions + immutable dataclasses — no I/O
    ├── db/repositories/ # Async Supabase data access, maps rows → domain models
    ├── services/        # Business logic, orchestrates repos + domain
    └── bot/             # Telegram: handlers, FSM states, keyboards, middleware
```

Services are injected into handlers via aiogram's Dispatcher data dict — handlers declare typed parameters and aiogram resolves them automatically.

---

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- A [Supabase](https://supabase.com) project
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

### Setup

```bash
git clone https://github.com/ichiesov/debt-resolver
cd debt-resolver

# Install dependencies
uv sync

# Copy and fill in environment variables
cp .env.example .env
```

`.env` required values:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_OWNER_ID=your_telegram_user_id
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
```

```bash
# Apply database migrations
uv run python scripts/migrate.py

# Run the bot
uv run python main.py
```

### Docker

```bash
docker compose up --build
```

---

## Development

```bash
# Lint + format
uv run ruff check . && uv run ruff format .

# Type-check
uv run mypy .

# Run tests
uv run pytest

# Tests with coverage
uv run pytest --cov=app --cov-report=term-missing
```

See [tech-docs/development.md](tech-docs/development.md) for full workflow, branching rules, and CI/CD.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12+ |
| Bot framework | aiogram 3.x |
| Database | Supabase (PostgreSQL) |
| Async client | supabase-py async |
| Validation | Pydantic v2 + pydantic-settings |
| Logging | structlog |
| Linter/formatter | ruff |
| Type checker | mypy (strict) |
| Tests | pytest + pytest-asyncio + freezegun |

---

## Documentation

- [Architecture](tech-docs/architecture.md) — Layer responsibilities, data flow, injection pattern
- [Bot Commands](tech-docs/bot-commands.md) — All commands and FSM conversation flows
- [Domain Logic](tech-docs/domain-logic.md) — Balance calculation, avalanche algorithm, recurring entry rules
- [Database](tech-docs/database.md) — Schema, repositories, migration workflow
- [Development](tech-docs/development.md) — Setup, testing, CI/CD, deployment
