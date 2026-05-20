# Development Guide

## Local Setup

```bash
# Clone and enter the repo
git clone https://github.com/ichiesov/debt-resolver
cd debt-resolver

# Install dependencies (uv creates .venv automatically)
uv sync

# Copy environment template
cp .env.example .env
# Fill in TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID, SUPABASE_URL, SUPABASE_KEY

# Apply migrations to your Supabase project
uv run python scripts/migrate.py

# Start the bot
uv run python main.py
```

### Docker

```bash
docker compose up --build
```

Services:
- `bot` — Telegram bot (built from `docker/bot/Dockerfile`)
- `web` — Placeholder web UI (built from `docker/web/Dockerfile`)

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✓ | Token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_OWNER_ID` | ✓ | Your Telegram user ID (bot refuses all other users) |
| `SUPABASE_URL` | ✓ | `https://your-project.supabase.co` |
| `SUPABASE_KEY` | ✓ | Service role key (not the anon key) |
| `LOG_LEVEL` | | Default: `INFO` |
| `ENVIRONMENT` | | Default: `development` |

---

## Commands

```bash
# Install / sync dependencies
uv sync

# Run the bot
uv run python main.py

# Lint (check only)
uv run ruff check .

# Format (in-place)
uv run ruff format .

# Type-check
uv run mypy .

# Run all tests
uv run pytest

# Run a single test file verbosely
uv run pytest tests/domain/test_balance.py -v

# Run tests with coverage report
uv run pytest --cov=app --cov-report=term-missing

# Apply SQL migrations
uv run python scripts/migrate.py

# Seed loans from Obsidian markdown
uv run python scripts/seed_loans.py
uv run python scripts/seed_loans.py --file ~/path/to/Кредиты.md
uv run python scripts/seed_loans.py --force   # re-seed even if already present
```

---

## Code Style

- **ruff** for linting and formatting, `line-length = 100`
- Selected rule sets: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort), `N` (naming), `W` (warnings), `UP` (pyupgrade)
- Run before every commit: `uv run ruff check . && uv run ruff format .`

---

## Type Safety

- **mypy strict mode** — every function must have complete type hints, including return types
- `# type: ignore` is allowed only with an explanation comment on the same line
- Use `from __future__ import annotations` at the top of every file (deferred evaluation)
- Use `typing.TYPE_CHECKING` for circular import breaks

---

## Testing

### Framework

- `pytest` with `asyncio_mode = "auto"` (all async tests run automatically)
- `pytest-mock` for mocking Supabase repositories
- `freezegun` for date-sensitive tests
- Target: >80% coverage

### Test Layout

```
tests/
├── conftest.py              # make_loan(), make_income(), make_expense(), make_borrowed()
├── domain/
│   ├── test_balance.py      # calculate_balance_for_date, calculate_forecast
│   └── test_optimization.py # rank_loans_by_avalanche
└── services/
    └── test_balance_service.py
```

### Writing Tests

Domain tests require no mocking:

```python
from decimal import Decimal
from datetime import date
from app.domain.balance import calculate_balance_for_date

def test_income_on_matching_date(make_income):
    income = make_income(amount=Decimal("5000"), entry_date=date(2024, 3, 15))
    result = calculate_balance_for_date(date(2024, 3, 15), [income], [], [], [], Decimal("0"))
    assert result.total_income == Decimal("5000")
    assert result.closing_balance == Decimal("5000")
```

Service tests mock all repositories:

```python
async def test_balance_service(mocker):
    income_repo = mocker.AsyncMock()
    income_repo.get_by_date_range.return_value = []
    # ... construct BalanceService with mocked repos
```

---

## Feature Workflow

Every feature goes through a branch and PR — direct commits to `master` are not allowed.

```bash
# 1. Branch from master
git checkout master && git pull origin master
git checkout -b feature/my-feature

# 2. Develop and commit
git commit -m "feat: ..."
git push origin feature/my-feature

# 3. Open PR
gh pr create --base master --title "..." --body "..."
```

### GitHub Actions

| Workflow | Trigger | Action |
|---|---|---|
| `code-review.yml` | PR opened / updated | Claude code review agent → PR comments |
| `apply-review.yml` | Review with `REQUEST_CHANGES` | Claude apply agent → commits fixes to branch |
| `auto-merge.yml` | Review with `APPROVED` | Auto-merges PR into master |
| `deploy.yml` | Push to `master` | Builds and deploys changed services to VPS |

Required GitHub secret: `ANTHROPIC_API_KEY`.

---

## Deployment (VPS)

### One-time VPS Setup

```bash
curl -fsSL https://get.docker.com | sh
mkdir -p /opt/debt-resolver
# Create /opt/debt-resolver/.env from .env.example
docker login ghcr.io -u <github-username> -p <PAT>
```

### CI/CD (`deploy.yml`)

Runs on every push to `master`. Uses `dorny/paths-filter` to detect which service changed:

| Filter | Paths |
|---|---|
| `bot` | `app/**`, `main.py`, `pyproject.toml`, `uv.lock`, `docker/bot/**` |
| `web` | `web/**`, `docker/web/**` |

Only changed services are rebuilt and deployed. Images pushed to `ghcr.io/ichiesov/`.

Required secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.

---

## Logging

Use `structlog` (not stdlib `logging`) for all new log statements:

```python
import structlog
log = structlog.get_logger()

log.info("payment_recorded", loan_id=str(loan_id), amount=str(amount))
```

Log level controlled via `LOG_LEVEL` env var (default: `INFO`).

---

## Adding a New Feature

Checklist:

1. Add domain models/functions if needed (pure, no I/O)
2. Add/update repository methods (data access only)
3. Add service method (business logic)
4. Add handler + FSM states if bot interaction needed
5. Register router in `app/bot/main.py`
6. Write tests for domain functions and services
7. Run `uv run ruff check . && uv run ruff format . && uv run mypy . && uv run pytest`
8. Commit and open PR
