alter table loans
  add column if not exists term_months smallint check (term_months > 0);
