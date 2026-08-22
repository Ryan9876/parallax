from pathlib import Path


def test_project_migration_preserves_owner_uniqueness_and_direct_client_lockdown():
    migration_path = Path(__file__).resolve().parents[1] / "migrations" / "20260822_0006_projects.sql"
    migration = migration_path.read_text(encoding="utf-8").lower()

    assert "create table if not exists projects" in migration
    assert "unique (owner_subject, slug)" in migration
    assert "unique (owner_subject, repository_ref)" in migration
    assert "unique (workspace_ref)" in migration
    assert "alter table projects enable row level security" in migration
    assert "revoke all on table projects from anon, authenticated" in migration
