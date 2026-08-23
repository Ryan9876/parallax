begin;

alter table conversations
    add column if not exists project_id varchar(36) null;

alter table engineering_runs
    add column if not exists project_id varchar(36) null;

create index if not exists ix_conversations_project_id
    on conversations (project_id);

create index if not exists ix_engineering_runs_project_id
    on engineering_runs (project_id);

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'fk_conversations_project_id_projects'
    ) then
        alter table conversations
            add constraint fk_conversations_project_id_projects
            foreign key (project_id) references projects(id) on delete restrict;
    end if;
end
$$;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'fk_engineering_runs_project_id_projects'
    ) then
        alter table engineering_runs
            add constraint fk_engineering_runs_project_id_projects
            foreign key (project_id) references projects(id) on delete restrict;
    end if;
end
$$;

-- Existing NULL values are intentionally preserved as historical/unbound.
-- New Code conversation and Engineering Run binding is enforced by the
-- protected API/service boundary; this migration does not invent backfills.

commit;
