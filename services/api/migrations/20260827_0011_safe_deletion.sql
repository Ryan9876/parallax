begin;

alter table conversations
    add column if not exists deleted_at timestamptz null;

alter table projects
    add column if not exists deleted_at timestamptz null;

create index if not exists ix_conversations_deleted_at
    on conversations (deleted_at);

create index if not exists ix_projects_deleted_at
    on projects (deleted_at);

alter table projects
    drop constraint if exists uq_projects_owner_slug;

alter table projects
    drop constraint if exists uq_projects_owner_repository;

create unique index if not exists uq_projects_owner_slug_active
    on projects (owner_subject, slug)
    where deleted_at is null;

create unique index if not exists uq_projects_owner_repository_active
    on projects (owner_subject, repository_ref)
    where deleted_at is null and repository_ref is not null;

commit;
