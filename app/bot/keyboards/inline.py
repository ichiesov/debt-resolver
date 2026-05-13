from __future__ import annotations

import uuid

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_cancel(confirm_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
        ]
    ])


def loan_list(loans: list[tuple[uuid.UUID, str]]) -> InlineKeyboardMarkup:
    """loans: list of (id, name) tuples."""
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"loan:{loan_id}")]
        for loan_id, name in loans
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def direction_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Я одолжил (мне должны)", callback_data="dir:lent"),
            InlineKeyboardButton(text="Я занял (я должен)", callback_data="dir:borrowed"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])


def yes_no(yes_data: str = "yes", no_data: str = "no") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data=yes_data),
            InlineKeyboardButton(text="Нет", callback_data=no_data),
        ]
    ])
