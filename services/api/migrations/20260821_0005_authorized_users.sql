begin;

create table if not exists authorized_users (
  id varchar(36) primary key,
  email varchar(320) not null,
  normalized_email varchar(320) not null,
  auth_user_id varchar(80),
  display_name varchar(160),
  avatar_url text,
  role varchar(16) not null default 'member',
  status varchar(16) not null default 'active',
  created_at timestamptz not null,
  updated_at timestamptz not null,
  last_login_at timestamptz,
  constraint uq_authorized_users_normalized_email unique(normalized_email),
  constraint uq_authorized_users_auth_user_id unique(auth_user_id),
  constraint ck_authorized_users_role check (role in ('owner', 'member')),
  constraint ck_authorized_users_status check (status in ('active', 'revoked'))
);

create index if not exists ix_authorized_users_status on authorized_users(status);
create index if not exists ix_authorized_users_role on authorized_users(role);

alter table authorized_users enable row level security;
revoke all on table authorized_users from anon, authenticated;

commit;
