from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.inline import yes_no
from app.bot.states.forms import AddIncomeForm
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


@router.message(Command("add_income"))
@router.message(F.text == "➕ Доход")
async def cmd_add_income(message: Message, state: FSMContext) -> None:
    await state.set_state(AddIncomeForm.amount)
    await message.answer("💰 Сумма дохода (₽):")


@router.message(AddIncomeForm.amount)
async def income_got_amount(message: Message, state: FSMContext) -> None:
    """Receive income amount and advance to AddIncomeForm.description."""
    try:
        amount = Decimal((message.text or "0").replace(" ", "").replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Введи корректную сумму (например: 50000)")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(AddIncomeForm.description)
    await message.answer("📝 Описание (например: Зарплата, Аванс, Фриланс):")


@router.message(AddIncomeForm.description)
async def income_got_description(message: Message, state: FSMContext) -> None:
    """Receive free-text description and advance to AddIncomeForm.entry_date."""
    if not message.text:
        return
    await state.update_data(description=message.text.strip())
    await state.set_state(AddIncomeForm.entry_date)
    await message.answer(
        "📅 Дата (сегодня/завтра, ДД.ММ или ДД.ММ.ГГГГ):\nИли отправь «сегодня» для текущей даты."
    )


@router.message(AddIncomeForm.entry_date)
async def income_got_date(message: Message, state: FSMContext) -> None:
    """Parse natural-language date and advance to AddIncomeForm.is_recurring."""
    parsed = _parse_date(message.text or "")
    if parsed is None:
        await message.answer(
            "❌ Не удалось распознать дату. Попробуй: сегодня, 15.05 или 15.05.2025"
        )
        return
    await state.update_data(entry_date=parsed.isoformat())
    await state.set_state(AddIncomeForm.is_recurring)
    await message.answer(
        "🔄 Это регулярный доход (повторяется каждый месяц)?",
        reply_markup=yes_no("inc_recurring_yes", "inc_recurring_no"),
    )


@router.callback_query(F.data == "inc_recurring_no", AddIncomeForm.is_recurring)
async def income_not_recurring(
    callback: CallbackQuery, state: FSMContext, transaction_service: TransactionService
) -> None:
    """Skip recurrence_day step and save immediately with is_recurring=False."""
    await state.update_data(is_recurring=False, recurrence_day=None)
    await _save_income(callback.message, state, transaction_service, edit=True)


@router.callback_query(F.data == "inc_recurring_yes", AddIncomeForm.is_recurring)
async def income_is_recurring(callback: CallbackQuery, state: FSMContext) -> None:
    """Mark income as recurring and advance to AddIncomeForm.recurrence_day."""
    await state.update_data(is_recurring=True)
    await state.set_state(AddIncomeForm.recurrence_day)
    await callback.message.edit_text("📅 В какой день месяца поступает этот доход? (1-31):")


@router.message(AddIncomeForm.recurrence_day)
async def income_got_recurrence_day(
    message: Message, state: FSMContext, transaction_service: TransactionService
) -> None:
    """Receive day-of-month (1-31) and save recurring income; end of FSM flow."""
    try:
        day = int((message.text or "0").strip())
        if not 1 <= day <= 31:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи число от 1 до 31")
        return
    await state.update_data(recurrence_day=day)
    await _save_income(message, state, transaction_service, edit=False)


async def _save_income(
    message: Message, state: FSMContext, transaction_service: TransactionService, *, edit: bool
) -> None:
    data = await state.get_data()
    entry = await transaction_service.add_income(
        amount=Decimal(data["amount"]),
        description=data["description"],
        category="income",
        entry_date=date.fromisoformat(data["entry_date"]),
        is_recurring=data.get("is_recurring", False),
        recurrence_day=data.get("recurrence_day"),
    )
    await state.clear()
    amount_fmt = f"{entry.amount:,.0f}".replace(",", " ")
    text = f"✅ Доход добавлен: {entry.description} — {amount_fmt} ₽"
    if edit:
        await message.edit_text(text)
    else:
        await message.answer(text)


@router.message(Command("incomes"))
async def cmd_incomes(message: Message, transaction_service: TransactionService) -> None:
    today = date.today()
    from_date = date(today.year, today.month, 1) if today.day >= 1 else today - timedelta(days=30)
    from_date = today - timedelta(days=30)
    entries = await transaction_service.get_recent_incomes(from_date, today)
    if not entries:
        await message.answer("За последние 30 дней доходов не найдено.")
        return
    lines = ["💰 <b>Доходы за последние 30 дней:</b>\n"]
    total = Decimal("0")
    for e in sorted(entries, key=lambda x: x.entry_date, reverse=True):
        amount_fmt = f"{e.amount:,.0f}".replace(",", " ")
        recurring = " 🔄" if e.is_recurring else ""
        lines.append(
            f"{e.entry_date.strftime('%d.%m')}  {amount_fmt} ₽  {e.description}{recurring}"
        )
        total += e.amount
    total_fmt = f"{total:,.0f}".replace(",", " ")
    lines.append(f"\n<b>Итого: {total_fmt} ₽</b>")
    await message.answer("\n".join(lines), parse_mode="HTML")
