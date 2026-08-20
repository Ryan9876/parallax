begin;

create table if not exists conversations (
  id varchar(36) primary key,
  title varchar(200) not null,
  mode varchar(20) not null,
  status varchar(40) not null,
  spec_id varchar(64) not null,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists messages (
  id varchar(36) primary key,
  conversation_id varchar(36) not null references conversations(id) on delete cascade,
  role varchar(20) not null,
  content text not null,
  status varchar(32) not null,
  created_at timestamptz not null
);
create index if not exists ix_messages_conversation_id on messages(conversation_id);

create table if not exists engineering_runs (
  id varchar(36) primary key,
  conversation_id varchar(36) not null references conversations(id) on delete cascade,
  spec_id varchar(64) not null,
  state varchar(32) not null,
  resume_stage varchar(32),
  revision integer not null,
  workspace_ref varchar(300),
  last_failure_code varchar(120),
  created_at timestamptz not null,
  updated_at timestamptz not null,
  completed_at timestamptz
);
create index if not exists ix_engineering_runs_conversation_id on engineering_runs(conversation_id);
create index if not exists ix_engineering_runs_spec_id on engineering_runs(spec_id);
create index if not exists ix_engineering_runs_state on engineering_runs(state);

create table if not exists engineering_attempts (
  id varchar(36) primary key,
  run_id varchar(36) not null references engineering_runs(id) on delete cascade,
  stage varchar(32) not null,
  attempt_number integer not null,
  operation_key varchar(160) not null,
  status varchar(32) not null,
  program_id varchar(160),
  model_id varchar(160),
  tool_id varchar(160),
  evidence_json text not null,
  failure_code varchar(120),
  started_at timestamptz not null,
  completed_at timestamptz not null,
  constraint uq_engineering_attempt_run_operation unique(run_id, operation_key),
  constraint uq_engineering_attempt_stage_number unique(run_id, stage, attempt_number)
);
create index if not exists ix_engineering_attempts_run_id on engineering_attempts(run_id);
create index if not exists ix_engineering_attempts_stage on engineering_attempts(stage);

commit;
