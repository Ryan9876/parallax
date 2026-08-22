begin;

create table if not exists projects (
    id varchar(36) primary key,
    owner_subject varchar(160) not null,
    slug varchar(80) not null,
    name varchar(120) not null,
    description text null,
    repository_ref varchar(240) null,
    workspace_ref varchar(100) not null,
    status varchar(24) not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_projects_owner_slug unique (owner_subject, slug),
    constraint uq_projects_owner_repository unique (owner_subject, repository_ref),
    constraint uq_projects_workspace_ref unique (workspace_ref)
);

create index if not exists ix_projects_owner_subject on projects (owner_subject);
create index if not exists ix_projects_status on projects (status);
create index if not exists ix_projects_owner_created on projects (owner_subject, created_at, id);

alter table projects enable row level security;
revoke all on table projects from anon, authenticated;

commit;
