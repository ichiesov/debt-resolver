from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.inline import direction_keyboard
from app.bot.states.forms import AddBorrowedForm
from app.services.transaction_service import TransactionService

router = Router()


def _parse_date(text: str) -> date | None:
    t = text.strip().lower()
    if t in ("сегодня", "today"):
        return date.today()
    if t == "завтра":
        return date.today() + timedelta(days=1)
    parts = t.split(".")
    try:
        if len(parts) == 2:
            return date(date.today().year, int(parts[1]), int(parts[0]))
        if len(parts) == 3:
            year = int(parts[2]) if len(parts[2]) == 4 else 2000 + int(parts[2])
            return date(year, int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        return None
    return None


@router.message(Command("lent"))
@router.message(F.text == "🤝 Долги")
async def cmd_lent(message: Message, transaction_service: TransactionService) -> None:
    entries = await transaction_service.get_lent()
    active = [e for e in entries if not e.is_settled]
    if not active:
        await message.answer(
            "У тебя нет активных долгов (мне должны).\n"
            "/add_debt — добавить долг\n"
            "/borrowed — я занял"
        )
        return
    lines = ["🤝 <b>Мне должны:</b>\n"]
    total = Decimal("0")
    for e in sorted(active, key=lambda x: x.transaction_date):
        amount_fmt = f"{e.remaining_amount:,.0f}".replace(",", " ")
        due = f"  до {e.expected_return_date.strftime('%d.%m.%Y')}" if e.expected_return_date else ""
        lines.append(f"👤 <b>{e.counterparty}</b>: {amount_fmt} ₽{due}")
        total += e.remaining_amount
    total_fmt = f"{total:,.0f}".replace(",", " ")
    lines.append(f"\n<b>Итого: {total_fmt} ₽</b>")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("borrowed"))
async def cmd_borrowed(message: Message, transaction_service: TransactionService) -> None:
    entries = await transaction_service.get_borrowed()
    active = [e for e in entries if not e.is_settled]
    if not active:
        await message.answer(
            "У тебя нет активных долгов (я должен).\n"
            "/add_debt — добавить долг\n"
            "/lent — мне должны"
        )
        return
    lines = ["💸 <b>Я должен:</b>\n"]
    total = Decimal("0")
    for e in sorted(active, key=lambda x: x.transaction_date):
        amount_fmt = f"{e.remaining_amount:,.0f}".replace(",", " ")
        due = f"  до {e.expected_return_date.strftime('%d.%m.%Y')}" if e.expected_return_date else ""
        lines.append(f"👤 <b>{e.counterparty}</b>: {amount_fmt} ₽{due}")
        total += e.remaining_amount
    total_fmt = f"{total:,.0f}".replace(",", " ")
    lines.append(f"\n<b>Итого: {total_fmt} ₽</b>")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("add_debt"))
async def cmd_add_debt(message: Message, state: FSMContext) -> None:
    await state.set_state(AddBorrowedForm.direction)
    await message.answer("↔️ Направление долга:", reply_markup=direction_keyboard())


@router.callback_query(F.data.startswith("dir:"), AddBorrowedForm.direction)
async def debt_got_direction(callback: CallbackQuery, state: FSMContext) -> None:
    direction = callback.data.split(":")[1]
    await state.update_data(direction=direction)
    await state.set_state(AddBorrowedForm.counterparty)
    label = "кто тебе должен" if direction == "lent" else "кому ты должен"
    await callback.message.edit_text(f"👤 Имя ({label}):")


@router.message(AddBorrowedForm.counterparty)
async def debt_got_counterparty(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    await state.update_data(counterparty=message.text.strip())
    await state.set_state(AddBorrowedForm.amount)
    await message.answer("💰 Сумма (₽):")


@router.message(AddBorrowedForm.amount)
async def debt_got_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal((message.text or "0").replace(" ", "").replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Введи корректную сумму")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(AddBorrowedForm.transaction_date)
    await message.answer("📅 Дата сделки (сегодня/завтра, ДД.ММ или ДД.ММ.ГГГГ):")


@router.message(AddBorrowedForm.transaction_date)
async def debt_got_transaction_date(message: Message, state: FSMContext) -> None:
    parsed = _parse_date(message.text or "")
    if parsed is None:
        await message.answer("❌ Не удалось распознать дату. Попробуй: сегодня, 15.05 или 15.05.2025")
        return
    await state.update_data(transaction_date=parsed.isoformat())
    await state.set_state(AddBorrowedForm.expected_return_date)
    await message.answer(
        "📅 Ожидаемая дата возврата (ДД.ММ или ДД.ММ.ГГГГ).\n"
        "Или отправь «нет», если срок не определён."
    )


@router.message(AddBorrowedForm.expected_return_date)
async def debt_got_return_date(message: Message, state: FSMContext, transaction_service: TransactionService) -> None:
    text = (message.text or "").strip().lower()
    return_date: date | None = None
    if text not in ("нет", "no", "-"):
        return_date = _parse_date(message.text or "")
        if return_date is None:
            await message.answer(
                "❌ Не удалось распознать дату. Попробуй: 15.05 или 15.05.2025\n"
                "Или отправь «нет» для пропуска."
            )
            return

    data = await state.get_data()
    entry = await transaction_service.add_borrowed(
        counterparty=data["counterparty"],
        direction=data["direction"],
        amount=Decimal(data["amount"]),
        transaction_date=date.fromisoformat(data["transaction_date"]),
        expected_return_date=return_date,
    )
    await state.clear()

    direction_label = "Одолжил" if entry.direction == "lent" else "Занял"
    amount_fmt = f"{entry.amount:,.0f}".replace(",", " ")
    due_text = f" (вернуть до {return_date.strftime('%d.%m.%Y')})" if return_date else ""
    await message.answer(
        f"✅ Долг добавлен\n{direction_label}: {entry.counterparty} — {amount_fmt} ₽{due_text}"
    )
