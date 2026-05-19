"""
Parse loan data from an Obsidian markdown note and seed the database.

Expected note format (blocks separated by blank lines):

    банк: Название банка
    сумма займа: 100000
    дата выдачи займа: 1 января 2024
    срок: 36 месяцев
    платеж в месяц: 3500
    процентная ставка: 20,00%
    остаток: 80000
    внесено платежей: 6
    дата платежа: 1 марта

Usage:
    uv run python scripts/seed_loans.py
    uv run python scripts/seed_loans.py --file /path/to/Кредиты.md
    uv run python scripts/seed_loans.py --force   # skip confirmation prompt
"""

import asyncio
import re
import sys
from argparse import ArgumentParser
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.db.client import get_client
from app.db.repositories.loan import LoanRepository
from app.db.repositories.user import UserRepository

_DEFAULT_NOTE = Path.home() / "Documents/obsidian-vaults/Projects/debt-resolver/data/Кредиты.md"

_MONTHS_RU = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def _parse_date(value: str) -> date:
    """Parse 'DD месяца YYYY' → date."""
    parts = value.strip().split()
    if len(parts) != 3:
        raise ValueError(f"Не могу разобрать дату: {value!r}")
    day, month_ru, year = int(parts[0]), parts[1].lower(), int(parts[2])
    if month_ru not in _MONTHS_RU:
        raise ValueError(f"Неизвестный месяц: {month_ru!r}")
    return date(year, _MONTHS_RU[month_ru], day)


def _parse_payment_day(value: str) -> int:
    """Parse '1 июня' or '25 мая' → day number."""
    return int(value.strip().split()[0])


def _parse_rate(value: str) -> Decimal:
    """Parse '19,99%' → Decimal('0.1999')."""
    cleaned = value.strip().rstrip("%").replace(",", ".")
    return Decimal(cleaned) / Decimal("100")


def _parse_amount(value: str) -> Decimal:
    return Decimal(value.strip().replace(" ", "").replace(",", "."))


def _parse_blocks(text: str) -> list[dict[str, str]]:
    """Split note into per-loan key-value blocks."""
    blocks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                blocks.append(current)
                current = {}
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            current[key.strip().lower()] = val.strip()
    if current:
        blocks.append(current)
    return blocks


def parse_note(path: Path) -> list[dict]:
    """Read the note and return a list of loan dicts ready for LoanRepository.create."""
    text = path.read_text(encoding="utf-8")
    blocks = _parse_blocks(text)
    loans = []
    for i, block in enumerate(blocks, 1):
        try:
            loans.append(
                {
                    "lender_name": block["банк"],
                    "principal_amount": _parse_amount(block["сумма займа"]),
                    "current_balance": _parse_amount(block["остаток"]),
                    "annual_interest_rate": _parse_rate(block["процентная ставка"]),
                    "monthly_payment": _parse_amount(block["платеж в месяц"]),
                    "payment_day": _parse_payment_day(block["дата платежа"]),
                    "start_date": _parse_date(block["дата выдачи займа"]),
                    "term_months": int(re.search(r"\d+", block["срок"]).group()),  # type: ignore[union-attr]
                    "loan_type": "consumer",
                }
            )
        except (KeyError, ValueError) as exc:
            print(f"⚠️  Блок #{i} пропущен: {exc}")
    return loans


async def seed(note_path: Path, *, force: bool) -> None:
    loans = parse_note(note_path)
    if not loans:
        print("❌ Не найдено кредитов для внесения.")
        return

    print(f"📋 Найдено {len(loans)} кредитов в {note_path.name}:")
    for idx, data in enumerate(loans, 1):
        pct = data["annual_interest_rate"] * Decimal("100")
        print(
            f"  {idx}. {data['lender_name']}  "
            f"{data['principal_amount']:,.0f} ₽  {pct:.2f}%  "
            f"остаток {data['current_balance']:,.0f} ₽"
        )

    if not force:
        answer = input("\nВнести в базу? [y/N] ").strip().lower()
        if answer not in ("y", "yes", "да"):
            print("Отменено.")
            return

    client = await get_client()
    user_repo = UserRepository(client)
    user_id = await user_repo.get_or_create(settings.telegram_owner_id)
    loan_repo = LoanRepository(client, user_id)

    existing = await loan_repo.get_all_active()
    existing_keys = {
        (loan.lender_name, loan.principal_amount, loan.start_date) for loan in existing
    }

    to_insert = [
        d for d in loans
        if (d["lender_name"], d["principal_amount"], d["start_date"]) not in existing_keys
    ]
    skipped = len(loans) - len(to_insert)
    if skipped:
        print(f"\n⏭  Пропущено {skipped} уже существующих кредитов.")
    if not to_insert:
        print("✅ Все кредиты уже в базе.")
        return

    for data in to_insert:
        loan = await loan_repo.create(
            lender_name=data["lender_name"],
            principal_amount=data["principal_amount"],
            current_balance=data["current_balance"],
            annual_interest_rate=data["annual_interest_rate"],
            monthly_payment=data["monthly_payment"],
            payment_day=data["payment_day"],
            start_date=data["start_date"],
            term_months=data["term_months"],
            loan_type=data["loan_type"],
        )
        pct = loan.annual_interest_rate * Decimal("100")
        print(
            f"✅ {loan.lender_name} | {loan.principal_amount:,.0f} ₽ | "
            f"{pct:.2f}% | остаток {loan.current_balance:,.0f} ₽"
        )

    print("\n✅ Готово.")


def main() -> None:
    parser = ArgumentParser(description="Seed loans from Obsidian note.")
    parser.add_argument(
        "--file",
        type=Path,
        default=_DEFAULT_NOTE,
        help="Path to the markdown note (default: %(default)s)",
    )
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"❌ Файл не найден: {args.file}")
        print("   Укажи путь через --file /путь/к/Кредиты.md")
        sys.exit(1)

    asyncio.run(seed(args.file, force=args.force))


if __name__ == "__main__":
    main()
