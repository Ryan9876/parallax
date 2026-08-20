begin;

alter table conversations enable row level security;
alter table messages enable row level security;
alter table engineering_runs enable row level security;
alter table engineering_attempts enable row level security;

revoke all on table conversations, messages, engineering_runs, engineering_attempts from anon, authenticated;

commit;
