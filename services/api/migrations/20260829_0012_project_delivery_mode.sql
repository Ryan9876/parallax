begin;

alter table projects
    add column if not exists delivery_mode varchar(32);

-- Preserve the historical behavior for every Project that existed before this migration.
update projects
set delivery_mode = 'vercel-preview'
where delivery_mode is null;

-- New Projects are provider-independent unless the caller explicitly selects Vercel.
alter table projects
    alter column delivery_mode set default 'source-only',
    alter column delivery_mode set not null;

alter table projects
    drop constraint if exists ck_projects_delivery_mode;

alter table projects
    add constraint ck_projects_delivery_mode
    check (delivery_mode in ('source-only', 'vercel-preview'));

commit;
