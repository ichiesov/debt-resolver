from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards.reply import main_menu

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Привет! Я помогу тебе отслеживать реальные деньги на каждый день.\n\n"
        "Используй кнопки меню или команды:\n"
        "/balance — баланс сегодня\n"
        "/forecast — прогноз на 30 дней\n"
        "/loans — кредиты\n"
        "/optimize — что гасить первым\n"
        "/add_income — добавить доход\n"
        "/add_expense — добавить расход\n"
        "/add_loan — добавить кредит",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 <b>Команды:</b>\n\n"
        "<b>Баланс</b>\n"
        "/balance [ДД.ММ] — баланс на дату\n"
        "/forecast [N] — прогноз на N дней\n\n"
        "<b>Доходы и расходы</b>\n"
        "/add_income — добавить доход\n"
        "/add_expense — добавить расход\n\n"
        "<b>Кредиты</b>\n"
        "/loans — список кредитов\n"
        "/add_loan — добавить кредит\n"
        "/pay_loan — записать платёж\n\n"
        "<b>Долги</b>\n"
        "/lent — я одолжил (мне должны)\n"
        "/borrowed — я занял (я должен)\n"
        "/add_debt — добавить долг\n\n"
        "<b>Оптимизация</b>\n"
        "/optimize — какой кредит гасить первым",
        parse_mode="HTML",
    )
