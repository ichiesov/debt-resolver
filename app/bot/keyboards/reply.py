from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📅 Прогноз")],
            [KeyboardButton(text="💳 Кредиты"), KeyboardButton(text="🎯 Оптимизация")],
            [KeyboardButton(text="➕ Доход"), KeyboardButton(text="➖ Расход")],
            [KeyboardButton(text="🤝 Долги")],
        ],
        resize_keyboard=True,
        persistent=True,
    )
