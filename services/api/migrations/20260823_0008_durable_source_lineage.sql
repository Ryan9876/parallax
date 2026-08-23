BEGIN;

CREATE TABLE IF NOT EXISTS source_lineage_manifests (
    lineage_id VARCHAR(68) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    run_id VARCHAR(36) NOT NULL,
    parent_lineage_id VARCHAR(68) NULL,
    manifest_sha256 VARCHAR(64) NOT NULL,
    manifest_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_source_lineage_id_format CHECK (lineage_id ~ '^src:[0-9a-f]{64}$'),
    CONSTRAINT ck_source_lineage_parent_format CHECK (
        parent_lineage_id IS NULL OR parent_lineage_id ~ '^src:[0-9a-f]{64}$'
    ),
    CONSTRAINT ck_source_lineage_manifest_sha CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE INDEX IF NOT EXISTS ix_source_lineage_manifests_project_run
    ON source_lineage_manifests(project_id, run_id);

CREATE TABLE IF NOT EXISTS source_lineage_heads (
    project_id VARCHAR(36) NOT NULL,
    run_id VARCHAR(36) NOT NULL,
    lineage_id VARCHAR(68) NOT NULL REFERENCES source_lineage_manifests(lineage_id) ON DELETE RESTRICT,
    revision BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (project_id, run_id),
    CONSTRAINT ck_source_lineage_head_format CHECK (lineage_id ~ '^src:[0-9a-f]{64}$'),
    CONSTRAINT ck_source_lineage_head_revision CHECK (revision >= 0)
);

-- Source bytes are intentionally absent from Postgres. Immutable source content
-- lives in private content-addressed object storage. This metadata contains only
-- bounded manifest evidence and the transactional current-lineage CAS head.

COMMIT;
