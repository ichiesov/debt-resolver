from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.keyboards.inline import yes_no
from app.bot.states.forms import AddExpenseForm
from app.services.transaction_service import TransactionService

router = Router()

CATEGORIES = [
    ("mortgage", "🏠 Ипотека"),
    ("car", "🚗 Авто"),
    ("food", "🛒 Продукты"),
    ("health", "💊 Здоровье"),
    ("entertainment", "🎮 Развлечения"),
    ("other", "📦 Другое"),
]


def _category_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(CATEGORIES), 2):
        row = [
            InlineKeyboardButton(text=label, callback_data=f"cat:{key}")
            for key, label in CATEGORIES[i:i + 2]
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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


@router.message(Command("add_expense"))
@router.message(F.text == "➖ Расход")
async def cmd_add_expense(message: Message, state: FSMContext) -> None:
    await state.set_state(AddExpenseForm.amount)
    await message.answer("💸 Сумма расхода (₽):")


@router.message(AddExpenseForm.amount)
async def expense_got_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal((message.text or "0").replace(" ", "").replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Введи корректную сумму (например: 3500)")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(AddExpenseForm.description)
    await message.answer("📝 Описание (например: Продукты, Бензин, Кино):")


@router.message(AddExpenseForm.description)
async def expense_got_description(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    await state.update_data(description=message.text.strip())
    await state.set_state(AddExpenseForm.category)
    await message.answer("🏷 Категория расхода:", reply_markup=_category_keyboard())


@router.callback_query(F.data.startswith("cat:"), AddExpenseForm.category)
async def expense_got_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(AddExpenseForm.entry_date)
    await callback.message.edit_text(
        "📅 Дата (сегодня/завтра, ДД.ММ или ДД.ММ.ГГГГ):\n"
        "Или отправь «сегодня» для текущей даты."
    )


@router.message(AddExpenseForm.entry_date)
async def expense_got_date(message: Message, state: FSMContext) -> None:
    parsed = _parse_date(message.text or "")
    if parsed is None:
        await message.answer("❌ Не удалось распознать дату. Попробуй: сегодня, 15.05 или 15.05.2025")
        return
    await state.update_data(entry_date=parsed.isoformat())
    await state.set_state(AddExpenseForm.is_recurring)
    await message.answer("🔄 Это регулярный расход (повторяется каждый месяц)?", reply_markup=yes_no("exp_recurring_yes", "exp_recurring_no"))


@router.callback_query(F.data == "exp_recurring_no", AddExpenseForm.is_recurring)
async def expense_not_recurring(callback: CallbackQuery, state: FSMContext, transaction_service: TransactionService) -> None:
    await state.update_data(is_recurring=False, recurrence_day=None)
    await _save_expense(callback.message, state, transaction_service, edit=True)


@router.callback_query(F.data == "exp_recurring_yes", AddExpenseForm.is_recurring)
async def expense_is_recurring(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(is_recurring=True)
    await state.set_state(AddExpenseForm.recurrence_day)
    await callback.message.edit_text("📅 В какой день месяца происходит этот расход? (1-31):")


@router.message(AddExpenseForm.recurrence_day)
async def expense_got_recurrence_day(message: Message, state: FSMContext, transaction_service: TransactionService) -> None:
    try:
        day = int((message.text or "0").strip())
        if not 1 <= day <= 31:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи число от 1 до 31")
        return
    await state.update_data(recurrence_day=day)
    await _save_expense(message, state, transaction_service, edit=False)


async def _save_expense(message: Message, state: FSMContext, transaction_service: TransactionService, *, edit: bool) -> None:
    data = await state.get_data()
    entry = await transaction_service.add_expense(
        amount=Decimal(data["amount"]),
        description=data["description"],
        category=data.get("category", "other"),
        entry_date=date.fromisoformat(data["entry_date"]),
        is_recurring=data.get("is_recurring", False),
        recurrence_day=data.get("recurrence_day"),
    )
    await state.clear()
    amount_fmt = f"{entry.amount:,.0f}".replace(",", " ")
    text = f"✅ Расход добавлен: {entry.description} — {amount_fmt} ₽"
    if edit:
        await message.edit_text(text)
    else:
        await message.answer(text)


@router.message(Command("expenses"))
async def cmd_expenses(message: Message, transaction_service: TransactionService) -> None:
    today = date.today()
    from_date = today - timedelta(days=30)
    entries = await transaction_service.get_recent_expenses(from_date, today)
    if not entries:
        await message.answer("За последние 30 дней расходов не найдено.")
        return
    lines = ["💸 <b>Расходы за последние 30 дней:</b>\n"]
    total = Decimal("0")
    for e in sorted(entries, key=lambda x: x.entry_date, reverse=True):
        amount_fmt = f"{e.amount:,.0f}".replace(",", " ")
        recurring = " 🔄" if e.is_recurring else ""
        lines.append(f"{e.entry_date.strftime('%d.%m')}  {amount_fmt} ₽  {e.description}{recurring}")
        total += e.amount
    total_fmt = f"{total:,.0f}".replace(",", " ")
    lines.append(f"\n<b>Итого: {total_fmt} ₽</b>")
    await message.answer("\n".join(lines), parse_mode="HTML")
