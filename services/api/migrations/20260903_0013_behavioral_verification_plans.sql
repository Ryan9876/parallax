begin;

create table if not exists behavioral_verification_plans (
  id varchar(36) primary key,
  work_specification_id varchar(36) not null references work_specifications(id) on delete cascade,
  work_specification_revision integer not null,
  work_specification_digest varchar(64) not null,
  revision integer not null,
  status varchar(24) not null default 'DRAFT',
  plan_json text not null,
  plan_digest varchar(64) not null,
  program_version varchar(100) not null,
  model_id varchar(160),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  approved_at timestamptz,
  constraint uq_behavioral_plan_spec_revision unique (work_specification_id, revision),
  constraint ck_behavioral_plan_revision_positive check (revision > 0),
  constraint ck_behavioral_plan_spec_revision_positive check (work_specification_revision > 0),
  constraint ck_behavioral_plan_status check (status in ('DRAFT', 'APPROVED', 'SUPERSEDED')),
  constraint ck_behavioral_plan_spec_digest check (work_specification_digest ~ '^[0-9a-f]{64}$'),
  constraint ck_behavioral_plan_digest check (plan_digest ~ '^[0-9a-f]{64}$'),
  constraint ck_behavioral_plan_json_size check (octet_length(plan_json) <= 32000)
);

create index if not exists ix_behavioral_verification_plans_work_specification_id
  on behavioral_verification_plans(work_specification_id);
create index if not exists ix_behavioral_verification_plans_status
  on behavioral_verification_plans(status);

alter table behavioral_verification_plans enable row level security;
revoke all on table behavioral_verification_plans from anon, authenticated;

commit;
