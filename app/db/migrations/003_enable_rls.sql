-- Enable Row Level Security on all tables.
-- The Python backend uses the service_role key which bypasses RLS entirely,
-- so no policies are needed. The anon key gets no access by default.

alter table users             enable row level security;
alter table accounts          enable row level security;
alter table income_entries    enable row level security;
alter table expense_entries   enable row level security;
alter table loans             enable row level security;
alter table loan_payments     enable row level security;
alter table borrowed_entries  enable row level security;
alter table p2p_repayments    enable row level security;
