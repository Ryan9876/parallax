begin;

create table if not exists work_specifications (
  id varchar(36) primary key,
  conversation_id varchar(36) not null references conversations(id) on delete cascade,
  revision integer not null,
  status varchar(24) not null default 'DRAFT',
  title varchar(120) not null,
  objective text not null,
  constraints_json text not null default '[]',
  acceptance_criteria_json text not null default '[]',
  risks_json text not null default '[]',
  open_questions_json text not null default '[]',
  confidence double precision not null default 0,
  program_version varchar(100) not null,
  model_id varchar(160),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  approved_at timestamptz,
  constraint uq_work_spec_conversation_revision unique (conversation_id, revision)
);

create index if not exists ix_work_specifications_conversation_id on work_specifications(conversation_id);
create index if not exists ix_work_specifications_status on work_specifications(status);
create index if not exists ix_work_specifications_updated_at on work_specifications(updated_at);

alter table work_specifications enable row level security;
revoke all on table work_specifications from anon, authenticated;

commit;
