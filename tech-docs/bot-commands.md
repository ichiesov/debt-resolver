# Bot Commands Reference

All user-facing text is in Russian. Bot is single-user — `OwnerMiddleware` silently drops all updates from unauthorized users.

---

## Main Menu

The reply keyboard shown after `/start` has 7 buttons:

```
[ 💰 Баланс  ]  [ 📅 Прогноз    ]
[ 💳 Кредиты ]  [ 🎯 Оптимизация ]
[ ➕ Доход   ]  [ ➖ Расход      ]
[       🤝 Долги               ]
```

Each button maps to the same handler as the corresponding command.

---

## Balance

### `/balance [ДД.ММ]` or `💰 Баланс`

Shows the balance breakdown for a single date (default: today).

Accepted date formats: `ДД.ММ` (current year assumed) · `ДД.ММ.ГГГГ`

Output includes:
- Opening balance
- Each income, expense, loan payment, and P2P transaction on that day
- Closing balance

### `/forecast [N]` or `📅 Прогноз`

Shows a rolling N-day forecast (default 30, clamped to 1–90).

One line per day: `DD.MM  +/- XXXXX ₽`

---

## Loans

### `/loans` or `💳 Кредиты`

Lists all active loans sorted by interest rate (descending). For each loan:

```
🏦 Тинькофф
  Остаток: 450 000 ₽
  Платёж: 18 500 ₽/мес (19.99%)
  День платежа: 15-е число
  Срок: 60 мес. · осталось ~38 мес.
```

### `/pay_loan`

Multi-step: select loan from inline keyboard → enter amount (0 = use default monthly payment).

Records a `scheduled` payment, decrements `current_balance`. If balance reaches ₽0, loan is automatically deactivated.

### `/add_loan`

Multi-step FSM form — 9 steps:

| Step | State | Input |
|---|---|---|
| 1 | `AddLoanForm.lender_name` | Bank/creditor name (free text) |
| 2 | `AddLoanForm.principal` | Original loan amount (₽) |
| 3 | `AddLoanForm.current_balance` | Current outstanding balance (₽) |
| 4 | `AddLoanForm.interest_rate` | Annual rate in % (0–100, e.g. `19.99`) → stored as fraction |
| 5 | `AddLoanForm.monthly_payment` | Monthly payment (₽) |
| 6 | `AddLoanForm.term_months` | Loan term in months |
| 7 | `AddLoanForm.payment_day` | Day of month for payment (1–31) |
| 8 | `AddLoanForm.loan_type` | Inline keyboard: Ипотека / Автокредит / Потребительский / Займ |
| 9 | `AddLoanForm.confirm` | Confirm / Cancel inline buttons |

`start_date` is set to today automatically.

---

## Income

### `/add_income` or `➕ Доход`

Multi-step FSM — 5–6 steps:

| Step | State | Input |
|---|---|---|
| 1 | `AddIncomeForm.amount` | Amount (₽) |
| 2 | `AddIncomeForm.description` | Description (free text) |
| 3 | `AddIncomeForm.entry_date` | Date (сегодня · завтра · ДД.ММ · ДД.ММ.ГГГГ) |
| 4 | `AddIncomeForm.is_recurring` | Да / Нет inline |
| 5 | `AddIncomeForm.recurrence_day` | Day of month (1–31), only if recurring |

### `/incomes`

Shows incomes from the last 30 days with a total sum.

---

## Expenses

### `/add_expense` or `➖ Расход`

Same flow as income, with an extra category step:

| Step | State | Input |
|---|---|---|
| 1 | `AddExpenseForm.amount` | Amount (₽) |
| 2 | `AddExpenseForm.description` | Description |
| 3 | `AddExpenseForm.category` | Inline: Ипотека / Авто / Продукты / Здоровье / Развлечения / Прочее |
| 4 | `AddExpenseForm.entry_date` | Date |
| 5 | `AddExpenseForm.is_recurring` | Да / Нет |
| 6 | `AddExpenseForm.recurrence_day` | Day of month (if recurring) |

### `/expenses`

Shows expenses from the last 30 days with a total sum.

---

## P2P Debts

### `/lent` or `🤝 Долги`

Lists entries where `direction = lent` (you lent money, they owe you). Shows remaining amount and expected return date if set.

### `/borrowed`

Lists entries where `direction = borrowed` (you owe someone). Shows remaining amount.

### `/add_debt`

Multi-step FSM — 4–5 steps:

| Step | State | Input |
|---|---|---|
| 1 | `AddBorrowedForm.direction` | Inline: Я одолжил (lent) / Я занял (borrowed) |
| 2 | `AddBorrowedForm.counterparty` | Person's name |
| 3 | `AddBorrowedForm.amount` | Amount (₽) |
| 4 | `AddBorrowedForm.transaction_date` | Date |
| 5 | `AddBorrowedForm.expected_return_date` | Return date or "нет" to skip |

---

## Optimization

### `/optimize` or `🎯 Оптимизация`

Shows debt avalanche ranking — active loans sorted by interest rate descending.

For each loan:
```
🥇 1. Тинькофф
   Ставка 19.99% — 7 485 ₽/мес. процентов
   Остаток: 450 000 ₽ · Платёж: 18 500 ₽
   ~38 мес. до закрытия
```

Followed by a short explanation of the avalanche method.

---

## Universal Cancel

Any inline button with `callback_data="cancel"` clears FSM state and shows "❌ Отменено". Registered at the `optimize` router level — works across all FSM flows.

---

## Date Parsing

Handlers that accept dates support these Russian-style formats:

| Input | Meaning |
|---|---|
| `сегодня` | `date.today()` |
| `завтра` | `date.today() + 1 day` |
| `ДД.ММ` | Current year assumed |
| `ДД.ММ.ГГ` | Two-digit year (2000 + YY) |
| `ДД.ММ.ГГГГ` | Full four-digit year |
