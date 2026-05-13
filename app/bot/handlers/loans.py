from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.keyboards.inline import confirm_cancel, loan_list
from app.bot.states.forms import AddLoanForm
from app.services.loan_service import LoanService

router = Router()

LOAN_TYPES = {
    "mortgage": "Ипотека",
    "car": "Автокредит",
    "consumer": "Потребительский",
    "personal": "Займ",
}


class PayLoanForm(StatesGroup):
    amount = State()


def _loan_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"ltype:{key}")]
        for key, label in LOAN_TYPES.items()
    ] + [[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]])


@router.message(Command("loans"))
@router.message(F.text == "💳 Кредиты")
async def cmd_loans(message: Message, loan_service: LoanService) -> None:
    loans = await loan_service.get_all_active()
    if not loans:
        await message.answer("У тебя нет активных кредитов. /add_loan — добавить кредит")
        return

    sorted_loans = sorted(loans, key=lambda l: l.annual_interest_rate, reverse=True)
    lines = ["💳 <b>Активные кредиты:</b>\n"]
    for loan in sorted_loans:
        pct = loan.annual_interest_rate * Decimal("100")
        balance_fmt = f"{loan.current_balance:,.0f}".replace(",", " ")
        payment_fmt = f"{loan.monthly_payment:,.0f}".replace(",", " ")
        lines.append(
            f"🏦 <b>{loan.lender_name}</b>\n"
            f"  Остаток: {balance_fmt} ₽\n"
            f"  Платёж: {payment_fmt} ₽/мес ({pct:.2f}%)\n"
            f"  День платежа: {loan.payment_day}-е число\n"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("pay_loan"))
async def cmd_pay_loan(message: Message, loan_service: LoanService) -> None:
    loans = await loan_service.get_all_active()
    if not loans:
        await message.answer("У тебя нет активных кредитов.")
        return
    keyboard = loan_list([(loan.id, loan.lender_name) for loan in loans])
    await message.answer("Выбери кредит для записи платежа:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("loan:"))
async def pay_loan_selected(callback: CallbackQuery, state: FSMContext, loan_service: LoanService) -> None:
    loan_id = uuid.UUID(callback.data.split(":")[1])
    loan = await loan_service.get_by_id(loan_id)
    payment_fmt = f"{loan.monthly_payment:,.0f}".replace(",", " ")
    await state.update_data(
        pay_loan_id=str(loan_id),
        pay_loan_name=loan.lender_name,
        pay_loan_default=str(loan.monthly_payment),
    )
    await state.set_state(PayLoanForm.amount)
    await callback.message.edit_text(
        f"💳 Платёж по кредиту <b>{loan.lender_name}</b>\n"
        f"Стандартный платёж: {payment_fmt} ₽\n\n"
        f"Введи сумму платежа (или 0 для стандартной суммы):",
        parse_mode="HTML",
    )


@router.message(PayLoanForm.amount)
async def pay_loan_amount(message: Message, state: FSMContext, loan_service: LoanService) -> None:
    try:
        raw = (message.text or "").replace(" ", "").replace(",", ".")
        amount_val = Decimal(raw)
        if amount_val < 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Введи корректную сумму")
        return

    data = await state.get_data()
    loan_id = uuid.UUID(data["pay_loan_id"])
    if amount_val == Decimal("0"):
        amount_val = Decimal(data["pay_loan_default"])

    await loan_service.record_payment(
        loan_id=loan_id,
        amount=amount_val,
        payment_date=date.today(),
    )
    await state.clear()
    amount_fmt = f"{amount_val:,.0f}".replace(",", " ")
    await message.answer(f"✅ Платёж {amount_fmt} ₽ по кредиту «{data['pay_loan_name']}» записан!")


@router.message(Command("add_loan"))
async def cmd_add_loan(message: Message, state: FSMContext) -> None:
    await state.set_state(AddLoanForm.lender_name)
    await message.answer("🏦 Название банка или кредитора (например: Тинькофф, Сбербанк):")


@router.message(AddLoanForm.lender_name)
async def loan_got_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    await state.update_data(lender_name=message.text.strip())
    await state.set_state(AddLoanForm.principal)
    await message.answer("💰 Первоначальная сумма кредита (₽):")


@router.message(AddLoanForm.principal)
async def loan_got_principal(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal((message.text or "0").replace(" ", "").replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Введи корректную сумму (например: 500000)")
        return
    await state.update_data(principal=str(amount))
    await state.set_state(AddLoanForm.current_balance)
    await message.answer("💸 Текущий остаток долга (₽):")


@router.message(AddLoanForm.current_balance)
async def loan_got_balance(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal((message.text or "0").replace(" ", "").replace(",", "."))
        if amount < 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Введи корректную сумму (например: 450000)")
        return
    await state.update_data(current_balance=str(amount))
    await state.set_state(AddLoanForm.interest_rate)
    await message.answer("📊 Процентная ставка (% годовых, например: 19.99):")


@router.message(AddLoanForm.interest_rate)
async def loan_got_rate(message: Message, state: FSMContext) -> None:
    try:
        rate = Decimal((message.text or "0").replace(",", "."))
        if rate < 0 or rate > 100:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Введи ставку в % от 0 до 100 (например: 19.99)")
        return
    await state.update_data(interest_rate=str(rate / Decimal("100")))
    await state.set_state(AddLoanForm.monthly_payment)
    await message.answer("💳 Ежемесячный платёж (₽):")


@router.message(AddLoanForm.monthly_payment)
async def loan_got_payment(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal((message.text or "0").replace(" ", "").replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Введи корректную сумму платежа")
        return
    await state.update_data(monthly_payment=str(amount))
    await state.set_state(AddLoanForm.payment_day)
    await message.answer("📅 День платежа (число месяца, 1-31):")


@router.message(AddLoanForm.payment_day)
async def loan_got_day(message: Message, state: FSMContext) -> None:
    try:
        day = int((message.text or "0").strip())
        if not 1 <= day <= 31:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи число от 1 до 31")
        return
    await state.update_data(payment_day=day)
    await state.set_state(AddLoanForm.loan_type)
    await message.answer("🏷 Тип кредита:", reply_markup=_loan_type_keyboard())


@router.callback_query(F.data.startswith("ltype:"), AddLoanForm.loan_type)
async def loan_got_type(callback: CallbackQuery, state: FSMContext) -> None:
    loan_type = callback.data.split(":")[1]
    await state.update_data(loan_type=loan_type)
    await state.set_state(AddLoanForm.confirm)
    data = await state.get_data()
    pct = Decimal(data["interest_rate"]) * Decimal("100")
    text = (
        f"✅ <b>Проверь данные:</b>\n\n"
        f"Кредитор: {data['lender_name']}\n"
        f"Тип: {LOAN_TYPES.get(loan_type, loan_type)}\n"
        f"Сумма: {Decimal(data['principal']):,.0f} ₽\n"
        f"Остаток: {Decimal(data['current_balance']):,.0f} ₽\n"
        f"Ставка: {pct:.2f}%\n"
        f"Платёж: {Decimal(data['monthly_payment']):,.0f} ₽/мес\n"
        f"День платежа: {data['payment_day']}-е число"
    )
    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=confirm_cancel("loan_confirm")
    )


@router.callback_query(F.data == "loan_confirm", AddLoanForm.confirm)
async def loan_confirmed(
    callback: CallbackQuery, state: FSMContext, loan_service: LoanService
) -> None:
    data = await state.get_data()
    await loan_service.add_loan(
        lender_name=data["lender_name"],
        principal_amount=Decimal(data["principal"]),
        current_balance=Decimal(data["current_balance"]),
        annual_interest_rate=Decimal(data["interest_rate"]),
        monthly_payment=Decimal(data["monthly_payment"]),
        payment_day=int(data["payment_day"]),
        start_date=date.today(),
        loan_type=data["loan_type"],
    )
    await state.clear()
    await callback.message.edit_text(f"✅ Кредит «{data['lender_name']}» добавлен!")


@router.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Отменено")
