-- Balance queries filter by user_id + date range
create index idx_income_user_date     on income_entries  (user_id, entry_date) where deleted_at is null;
create index idx_expense_user_date    on expense_entries (user_id, entry_date) where deleted_at is null;
create index idx_loans_user_active    on loans           (user_id, is_active)  where deleted_at is null;
create index idx_borrowed_user        on borrowed_entries(user_id, is_settled) where deleted_at is null;
create index idx_loan_payments_loan   on loan_payments   (loan_id, payment_date);
create index idx_p2p_repayments_entry on p2p_repayments  (entry_id, repayment_date);
create unique index idx_users_telegram on users (telegram_id);
