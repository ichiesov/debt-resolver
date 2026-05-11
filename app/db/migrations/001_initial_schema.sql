-- Enable UUID generation
create extension if not exists "pgcrypto";

-- Shared trigger for updated_at
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Users (one record per bot owner, maps telegram_id to internal uuid)
create table users (
  id          uuid primary key default gen_random_uuid(),
  telegram_id bigint unique not null,
  username    text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create trigger users_updated_at before update on users
  for each row execute function set_updated_at();

-- Accounts (virtual wallets: bank account, cash, card)
create table accounts (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references users(id) on delete cascade,
  name        text not null,
  currency    char(3) not null default 'RUB',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  deleted_at  timestamptz
);
create trigger accounts_updated_at before update on accounts
  for each row execute function set_updated_at();

-- Income entries (one-time or recurring)
create table income_entries (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references users(id) on delete cascade,
  account_id      uuid references accounts(id),
  amount          numeric(15,2) not null check (amount > 0),
  description     text not null,
  category        text not null default 'other',
  entry_date      date not null,
  is_recurring    boolean not null default false,
  recurrence_day  smallint check (recurrence_day between 1 and 31),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  deleted_at      timestamptz
);
create trigger income_entries_updated_at before update on income_entries
  for each row execute function set_updated_at();

-- Expense entries (one-time or recurring)
create table expense_entries (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references users(id) on delete cascade,
  account_id      uuid references accounts(id),
  amount          numeric(15,2) not null check (amount > 0),
  description     text not null,
  category        text not null default 'other',
  entry_date      date not null,
  is_recurring    boolean not null default false,
  recurrence_day  smallint check (recurrence_day between 1 and 31),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  deleted_at      timestamptz
);
create trigger expense_entries_updated_at before update on expense_entries
  for each row execute function set_updated_at();

-- Loans (bank credits, mortgages, car loans, personal loans)
create table loans (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null references users(id) on delete cascade,
  lender_name          text not null,
  principal_amount     numeric(15,2) not null check (principal_amount > 0),
  current_balance      numeric(15,2) not null check (current_balance >= 0),
  annual_interest_rate numeric(6,4) not null check (annual_interest_rate >= 0),
  monthly_payment      numeric(15,2) not null check (monthly_payment > 0),
  payment_day          smallint not null check (payment_day between 1 and 31),
  start_date           date not null,
  end_date             date,
  loan_type            text not null default 'consumer'
                         check (loan_type in ('mortgage','car','consumer','personal')),
  is_active            boolean not null default true,
  notes                text,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  deleted_at           timestamptz
);
create trigger loans_updated_at before update on loans
  for each row execute function set_updated_at();

-- Loan payments log
create table loan_payments (
  id              uuid primary key default gen_random_uuid(),
  loan_id         uuid not null references loans(id) on delete cascade,
  user_id         uuid not null references users(id) on delete cascade,
  amount          numeric(15,2) not null check (amount > 0),
  principal_part  numeric(15,2) check (principal_part >= 0),
  interest_part   numeric(15,2) check (interest_part >= 0),
  payment_date    date not null,
  payment_type    text not null default 'scheduled'
                    check (payment_type in ('scheduled','early','partial')),
  created_at      timestamptz not null default now()
);

-- P2P borrowed/lent entries
create table borrowed_entries (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null references users(id) on delete cascade,
  counterparty         text not null,
  direction            text not null check (direction in ('lent','borrowed')),
  amount               numeric(15,2) not null check (amount > 0),
  description          text,
  transaction_date     date not null,
  expected_return_date date,
  is_settled           boolean not null default false,
  settled_at           timestamptz,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  deleted_at           timestamptz
);
create trigger borrowed_entries_updated_at before update on borrowed_entries
  for each row execute function set_updated_at();

-- P2P repayments log
create table p2p_repayments (
  id              uuid primary key default gen_random_uuid(),
  entry_id        uuid not null references borrowed_entries(id) on delete cascade,
  user_id         uuid not null references users(id) on delete cascade,
  amount          numeric(15,2) not null check (amount > 0),
  repayment_date  date not null,
  notes           text,
  created_at      timestamptz not null default now()
);
