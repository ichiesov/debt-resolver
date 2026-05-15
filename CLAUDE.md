# debt-resolver — Claude Code Agent Guide

## Project Summary

**debt-resolver** is a personal finance tracker for managing debts and loans.

- **Backend**: Python 3.12+, async throughout
- **Bot interface**: aiogram 3.x Telegram bot (all user-facing text in Russian)
- **Database**: Supabase (PostgreSQL via supabase-py async client)
- **Currency**: All monetary amounts stored and displayed in RUB (Russian rubles)
- **Owner**: Single-user bot — access is guarded by `TELEGRAM_OWNER_ID` middleware

---

## Architecture Overview

```
debt-resolver/
├── main.py                     # Entry point: asyncio.run(run_bot())
├── app/
│   ├── domain/                 # Pure domain models (Pydantic), no I/O
│   ├── db/
│   │   ├── repositories/       # Async Supabase repository classes
│   │   └── migrations/         # Raw SQL migration files (no __init__.py)
│   ├── services/               # Business logic, orchestrates domain + repos
│   └── bot/
│       ├── main.py             # Bot setup: Dispatcher, router registration, polling
│       ├── middleware/         # OwnerMiddleware and other aiogram middleware
│       ├── filters/            # Custom aiogram filters
│       ├── keyboards/          # InlineKeyboardMarkup / ReplyKeyboardMarkup builders
│       ├── states/             # FSMContext state groups
│       └── handlers/           # Aiogram routers grouped by feature
├── tests/
│   ├── domain/
│   └── services/
├── web/                        # Placeholder for future web UI
└── ios/                        # Placeholder for future iOS app
```

### Layer responsibilities

| Layer | Responsibility |
|---|---|
| `domain` | Pydantic models, value objects, enums — zero side effects |
| `db/repositories` | All Supabase async calls, maps raw dicts to domain models, casts numerics |
| `services` | Business rules: validation, calculations, cross-repo orchestration |
| `bot` | Telegram interaction only — delegates all logic to services |

---

## How to Run

```bash
# Install dependencies (uses uv lockfile)
uv sync

# Copy and fill in environment variables
cp .env.example .env

# Start the bot
uv run python main.py
```

---

## Обязательный процесс разработки (Feature Workflow)

**Каждая фича разрабатывается в отдельной ветке и проходит через PR.**

### Шаги

```
1. Создать ветку от master
   git checkout master && git pull origin master
   git checkout -b feature/<название>

2. Разрабатывать, коммитить в feature-ветку
   git commit -m "feat: ..."
   git push origin feature/<название>

3. Создать PR в GitHub (base: master)
   gh pr create --base master --title "..." --body "..."

4. GitHub Actions автоматически:
   a. Запускает code-review агента (Claude) → оставляет комментарии в PR
   b. Если запрошены изменения → apply-review агент вносит их в ветку
   c. После апрува (человеком) → PR автоматически вливается в master
```

### GitHub Actions workflows

| Workflow | Триггер | Действие |
|---|---|---|
| `code-review.yml` | PR открыт / обновлён | Claude code review agent → комментарии и review в PR |
| `apply-review.yml` | Review с `REQUEST_CHANGES` | Claude apply agent → вносит изменения и коммитит в ветку |
| `auto-merge.yml` | Review с `APPROVED` | Автоматически вливает PR в master |

### Правила

- **Нельзя** коммитить напрямую в `master`
- PR без прохождения code review агента не мержится
- Человек может апрувить PR даже если агент запросил изменения
- После апрува ветка удаляется автоматически

### Необходимые секреты в GitHub

| Secret | Где взять |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |

---

## MCP Servers

| Server | Purpose | URL |
|---|---|---|
| `supabase` | Schema inspection, running migrations, querying data | `https://mcp.supabase.com/mcp` |
| `obsidian-vault` | Write project documentation to Obsidian vault at `Projects/debt-resolver` | `http://localhost:3001/mcp` |

---

## Agent Workflow

Use the correct agent/skill for each task type to get optimal results:

| Task | Agent/Skill |
|---|---|
| Schema design / migration review | `database-design:postgresql` |
| Feature implementation | `backend-development:feature-development` |
| Project scaffold / module layout | `python-development:python-project-structure` |
| Type hints, mypy | `python-development:python-type-safety` |
| Design patterns, SOLID | `python-development:python-design-patterns` |
| Error handling | `python-development:python-error-handling` |
| Test generation | `unit-testing:test-generate` |
| Documentation (docstrings + Obsidian) | `code-documentation:doc-generate` |
| Async patterns (aiogram, asyncio) | `python-development:async-python-patterns` |
| Pre-release review | `comprehensive-review:full-review` |
| Python config / env vars | `python-development:python-configuration` |
| Code style, ruff, formatting | `python-development:python-code-style` |

---

## Coding Rules

### Monetary values
- Always use `decimal.Decimal` for monetary values — **never `float`**
- Supabase returns `numeric` columns as Python strings — always cast to `Decimal` in repositories before passing to domain models or services

```python
# Correct
from decimal import Decimal
amount = Decimal(row["amount"])

# Wrong
amount = float(row["amount"])
amount = row["amount"]  # raw string from Supabase
```

### Async / I/O
- All Supabase calls are async — **no sync I/O anywhere in the call stack**
- Use `await` on every supabase-py client call
- Never call blocking I/O inside `async def` without `asyncio.to_thread`

### Type safety
- mypy strict mode is enforced — **every function must have type hints**, including return types
- No `# type: ignore` comments without an accompanying explanation comment
- Use `typing.TYPE_CHECKING` imports to break circular deps when needed

### Code style
- **ruff** for linting and formatting (`line-length = 100`)
- Selected rules: `E`, `F`, `I`, `N`, `W`, `UP` (see `pyproject.toml`)
- Run before committing: `uv run ruff check . && uv run ruff format .`

### Bot access control
- `TELEGRAM_OWNER_ID` environment variable holds the single authorized Telegram user ID
- An `OwnerMiddleware` (in `app/bot/middleware/`) must check every incoming update
- Unauthorized users receive a silent rejection (no response) or a brief "not authorized" message

### Date parsing
The bot accepts natural-language Russian dates. Supported formats:

| Input | Meaning |
|---|---|
| `сегодня` | today |
| `завтра` | tomorrow |
| `DD.MM` | day and month (current year assumed) |
| `DD.MM.YY` | day, month, two-digit year |

### Repository pattern
- One repository class per domain aggregate (e.g., `DebtRepository`, `PersonRepository`)
- Repositories return domain model instances, not raw dicts
- All numeric fields from Supabase must be cast to `Decimal` in the repository layer

### Error handling
- Use custom exception classes defined in `app/domain/` or `app/services/`
- Bot handlers catch service exceptions and translate them to user-friendly Russian messages
- Never let unhandled exceptions propagate to the Telegram API

### Testing
- Target: >80% coverage
- Use `pytest-asyncio` with `asyncio_mode = "auto"`
- Mock Supabase client with `pytest-mock`
- Use `freezegun` for date-sensitive tests
- Tests live in `tests/domain/` and `tests/services/` (no bot handler tests required initially)
