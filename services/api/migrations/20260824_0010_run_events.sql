BEGIN;

CREATE TABLE IF NOT EXISTS engineering_run_events (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    run_id VARCHAR(36) NOT NULL REFERENCES engineering_runs(id) ON DELETE CASCADE,
    sequence BIGINT NOT NULL,
    event_key VARCHAR(160) NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    stage VARCHAR(32) NULL,
    outcome VARCHAR(32) NOT NULL,
    subsystem VARCHAR(32) NOT NULL,
    attempt_id VARCHAR(36) NULL,
    worker_execution_id VARCHAR(36) NULL,
    source_lineage_ref VARCHAR(68) NULL,
    parent_source_lineage_ref VARCHAR(68) NULL,
    operation_ref VARCHAR(200) NULL,
    artifact_ref VARCHAR(200) NULL,
    evidence_ref VARCHAR(200) NULL,
    failure_code VARCHAR(120) NULL,
    summary VARCHAR(360) NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_engineering_run_event_sequence UNIQUE (run_id, sequence),
    CONSTRAINT uq_engineering_run_event_key UNIQUE (run_id, event_key),
    CONSTRAINT ck_engineering_run_event_sequence_positive CHECK (sequence > 0),
    CONSTRAINT ck_engineering_run_event_type CHECK (event_type IN (
        'RUN_CREATED', 'STAGE_RESULT', 'OPERATION_REPLAY', 'RUN_CONTROL',
        'SOURCE_LINEAGE_ACCEPTED', 'SOURCE_DELIVERY', 'PROVIDER_RESULT',
        'EVALUATION_RESULT', 'WORKER_STATE', 'REVIEW_REQUIRED'
    )),
    CONSTRAINT ck_engineering_run_event_stage CHECK (
        stage IS NULL OR stage IN (
            'SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW',
            'COMPLETE', 'PAUSED', 'FAILED', 'SPEC_AMENDMENT', 'CANCELLED'
        )
    ),
    CONSTRAINT ck_engineering_run_event_outcome CHECK (outcome IN (
        'STARTED', 'PROGRESSED', 'SUCCEEDED', 'FAILED', 'DENIED',
        'REPLAYED', 'RECOVERING', 'HUMAN_REQUIRED', 'INFO'
    )),
    CONSTRAINT ck_engineering_run_event_subsystem CHECK (subsystem IN (
        'RUN', 'IMPLEMENTATION', 'EXECUTION', 'WORKER', 'SOURCE_LINEAGE',
        'GITHUB', 'VERCEL', 'EVALUATION', 'REVIEW'
    )),
    CONSTRAINT ck_engineering_run_event_source_lineage CHECK (
        source_lineage_ref IS NULL OR source_lineage_ref ~ '^src:[0-9a-f]{64}$'
    ),
    CONSTRAINT ck_engineering_run_event_parent_lineage CHECK (
        parent_source_lineage_ref IS NULL OR parent_source_lineage_ref ~ '^src:[0-9a-f]{64}$'
    ),
    CONSTRAINT ck_engineering_run_event_failure_code CHECK (
        failure_code IS NULL OR failure_code ~ '^[A-Z][A-Z0-9_:-]{0,119}$'
    ),
    CONSTRAINT ck_engineering_run_event_summary_size CHECK (
        summary IS NULL OR char_length(summary) <= 360
    ),
    CONSTRAINT ck_engineering_run_event_metadata_size CHECK (
        char_length(metadata_json) <= 4000
    )
);

CREATE INDEX IF NOT EXISTS ix_engineering_run_events_project
    ON engineering_run_events(project_id);
CREATE INDEX IF NOT EXISTS ix_engineering_run_events_run_sequence
    ON engineering_run_events(run_id, sequence);
CREATE INDEX IF NOT EXISTS ix_engineering_run_events_stage
    ON engineering_run_events(stage);
CREATE INDEX IF NOT EXISTS ix_engineering_run_events_worker
    ON engineering_run_events(worker_execution_id);
CREATE INDEX IF NOT EXISTS ix_engineering_run_events_lineage
    ON engineering_run_events(source_lineage_ref);

ALTER TABLE engineering_run_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE engineering_run_events FROM anon, authenticated;

-- Wave 4 events are a server-owned append-only observation projection. They do
-- not replace Engineering Run attempts, worker lease/checkpoint state, durable
-- source lineage, provider audit/evidence, or protected evaluation authority.

COMMIT;
