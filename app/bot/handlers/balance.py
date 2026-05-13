from __future__ import annotations

from datetime import date
from decimal import Decimal

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards.reply import main_menu
from app.domain.models import DailyBalance
from app.services.balance_service import BalanceService

router = Router()


def _fmt_amount(amount: Decimal) -> str:
    return f"{amount:,.0f} ₽".replace(",", " ")


def _format_balance(b: DailyBalance) -> str:
    sign = "+" if b.closing_balance >= Decimal("0") else ""
    lines = [
        f"📅 <b>{b.date.strftime('%d.%m.%Y')}</b>",
        f"Остаток на начало: {_fmt_amount(b.opening_balance)}",
        "",
    ]
    if b.breakdown:
        for item in b.breakdown:
            prefix = "➕" if item.is_positive else "➖"
            lines.append(f"  {prefix} {item.label}: {_fmt_amount(item.amount)}")
        lines.append("")
    lines.append(f"💰 <b>Итого: {sign}{_fmt_amount(b.closing_balance)}</b>")
    return "\n".join(lines)


@router.message(Command("balance"))
@router.message(lambda m: m.text == "💰 Баланс")
async def cmd_balance(message: Message, balance_service: BalanceService) -> None:
    args = (message.text or "").split()
    target = date.today()
    if len(args) > 1:
        try:
            parts = args[1].split(".")
            if len(parts) == 2:
                target = date(date.today().year, int(parts[1]), int(parts[0]))
            elif len(parts) == 3:
                year = int(parts[2]) if len(parts[2]) == 4 else 2000 + int(parts[2])
                target = date(year, int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            await message.answer("❌ Неверный формат даты. Используй ДД.ММ или ДД.ММ.ГГГГ")
            return

    balance = await balance_service.get_balance_for_date(target)
    await message.answer(_format_balance(balance), parse_mode="HTML")


@router.message(Command("forecast"))
@router.message(lambda m: m.text == "📅 Прогноз")
async def cmd_forecast(message: Message, balance_service: BalanceService) -> None:
    args = (message.text or "").split()
    days = 30
    if len(args) > 1:
        try:
            days = max(1, min(90, int(args[1])))
        except ValueError:
            pass

    forecast = await balance_service.get_forecast(date.today(), days)
    lines = [f"📊 <b>Прогноз на {days} дней:</b>\n"]
    for daily in forecast:
        sign = "+" if daily.closing_balance >= Decimal("0") else ""
        lines.append(
            f"{daily.date.strftime('%d.%m')}  {sign}{_fmt_amount(daily.closing_balance)}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")
