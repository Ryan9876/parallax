begin;

alter table projects
    add column if not exists delivery_mode varchar(32);

update projects
set delivery_mode = 'vercel-preview'
where delivery_mode is null;

alter table projects
    alter column delivery_mode set default 'vercel-preview',
    alter column delivery_mode set not null;

alter table projects
    drop constraint if exists ck_projects_delivery_mode;

alter table projects
    add constraint ck_projects_delivery_mode
    check (delivery_mode in ('source-only', 'vercel-preview'));

commit;
