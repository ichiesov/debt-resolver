from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.optimization_service import OptimizationService

router = Router()


@router.message(Command("optimize"))
@router.message(F.text == "🎯 Оптимизация")
async def cmd_optimize(message: Message, optimization_service: OptimizationService) -> None:
    recs = await optimization_service.get_recommendations()
    if not recs:
        await message.answer(
            "🎉 У тебя нет активных кредитов — поздравляю!\n"
            "Добавь кредиты через /add_loan"
        )
        return

    lines = ["🎯 <b>Стратегия погашения (метод лавины):</b>\n"]
    for rec in recs:
        medal = ["🥇", "🥈", "🥉"][rec.rank - 1] if rec.rank <= 3 else f"{rec.rank}."
        balance_fmt = f"{rec.loan.current_balance:,.0f}".replace(",", " ")
        payment_fmt = f"{rec.loan.monthly_payment:,.0f}".replace(",", " ")
        lines.append(
            f"{medal} <b>{rec.loan.lender_name}</b>\n"
            f"  {rec.reason}\n"
            f"  Остаток: {balance_fmt} ₽  |  Платёж: {payment_fmt} ₽/мес\n"
            f"  До закрытия: ~{rec.months_to_payoff} мес.\n"
        )

    lines.append(
        "\n💡 Метод лавины: гасить досрочно кредит с наивысшей ставкой — "
        "так ты платишь меньше процентов в сумме."
    )
    await message.answer("\n".join(lines), parse_mode="HTML")
