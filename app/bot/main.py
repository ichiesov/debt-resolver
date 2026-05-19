from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import balance, borrowed, expense, income, loans, optimize, start
from app.bot.middleware.auth import OwnerMiddleware
from app.config import settings
from app.db.client import get_client
from app.db.repositories import (
    BorrowedRepository,
    ExpenseRepository,
    IncomeRepository,
    LoanPaymentRepository,
    LoanRepository,
    UserRepository,
)
from app.services import BalanceService, LoanService, OptimizationService, TransactionService


async def run_bot() -> None:
    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(OwnerMiddleware())
    dp.callback_query.middleware(OwnerMiddleware())

    client = await get_client()
    user_repo = UserRepository(client)
    user_id = await user_repo.get_or_create(settings.telegram_owner_id)

    income_repo = IncomeRepository(client, user_id)
    expense_repo = ExpenseRepository(client, user_id)
    loan_repo = LoanRepository(client, user_id)
    payment_repo = LoanPaymentRepository(client, user_id)
    borrowed_repo = BorrowedRepository(client, user_id)

    dp["balance_service"] = BalanceService(income_repo, expense_repo, loan_repo, borrowed_repo)
    dp["loan_service"] = LoanService(loan_repo, payment_repo)
    dp["transaction_service"] = TransactionService(income_repo, expense_repo, borrowed_repo)
    dp["optimization_service"] = OptimizationService(loan_repo)

    for router in [
        start.router,
        balance.router,
        loans.router,
        income.router,
        expense.router,
        borrowed.router,
        optimize.router,
    ]:
        dp.include_router(router)

    await dp.start_polling(bot)
