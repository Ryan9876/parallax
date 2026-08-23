BEGIN;

CREATE TABLE IF NOT EXISTS engineering_worker_executions (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL REFERENCES engineering_runs(id) ON DELETE CASCADE,
    state VARCHAR(32) NOT NULL DEFAULT 'RUNNING',
    lease_owner_id VARCHAR(64) NULL,
    lease_generation BIGINT NOT NULL DEFAULT 0,
    lease_expires_at TIMESTAMPTZ NULL,
    last_meaningful_progress_at TIMESTAMPTZ NULL,
    checkpoint_revision BIGINT NOT NULL DEFAULT 0,
    checkpoint_json TEXT NOT NULL DEFAULT '{}',
    current_step VARCHAR(64) NULL,
    source_lineage_ref VARCHAR(68) NULL,
    last_known_good_lineage_ref VARCHAR(68) NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    no_progress_count INTEGER NOT NULL DEFAULT 0,
    oscillation_count INTEGER NOT NULL DEFAULT 0,
    progress_fingerprint VARCHAR(64) NULL,
    previous_progress_fingerprint VARCHAR(64) NULL,
    stall_classification VARCHAR(64) NULL,
    blocker_code VARCHAR(120) NULL,
    next_recovery_action VARCHAR(64) NULL,
    revision BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_engineering_worker_execution_run UNIQUE (run_id),
    CONSTRAINT ck_worker_state CHECK (state IN (
        'RUNNING', 'PROGRESSING', 'CHECKPOINTED', 'STALLED', 'RECOVERING',
        'REASSIGNED', 'HUMAN_REQUIRED', 'READY_FOR_INTEGRATION', 'SUCCEEDED', 'FAILED'
    )),
    CONSTRAINT ck_worker_lease_generation_nonnegative CHECK (lease_generation >= 0),
    CONSTRAINT ck_worker_checkpoint_revision_nonnegative CHECK (checkpoint_revision >= 0),
    CONSTRAINT ck_worker_retry_count_nonnegative CHECK (retry_count >= 0),
    CONSTRAINT ck_worker_no_progress_count_nonnegative CHECK (no_progress_count >= 0),
    CONSTRAINT ck_worker_oscillation_count_nonnegative CHECK (oscillation_count >= 0),
    CONSTRAINT ck_worker_revision_nonnegative CHECK (revision >= 0),
    CONSTRAINT ck_worker_lease_pair CHECK (
        (lease_owner_id IS NULL AND lease_expires_at IS NULL) OR
        (lease_owner_id IS NOT NULL AND lease_expires_at IS NOT NULL)
    ),
    CONSTRAINT ck_worker_lease_owner_format CHECK (
        lease_owner_id IS NULL OR lease_owner_id ~ '^worker:[0-9a-f-]{36}$'
    ),
    CONSTRAINT ck_worker_checkpoint_size CHECK (char_length(checkpoint_json) <= 12000),
    CONSTRAINT ck_worker_source_lineage_format CHECK (
        source_lineage_ref IS NULL OR source_lineage_ref ~ '^src:[0-9a-f]{64}$'
    ),
    CONSTRAINT ck_worker_lkg_lineage_format CHECK (
        last_known_good_lineage_ref IS NULL OR last_known_good_lineage_ref ~ '^src:[0-9a-f]{64}$'
    ),
    CONSTRAINT ck_worker_progress_fingerprint_format CHECK (
        progress_fingerprint IS NULL OR progress_fingerprint ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT ck_worker_previous_fingerprint_format CHECK (
        previous_progress_fingerprint IS NULL OR previous_progress_fingerprint ~ '^[0-9a-f]{64}$'
    )
);

CREATE INDEX IF NOT EXISTS ix_engineering_worker_executions_state
    ON engineering_worker_executions(state);
CREATE INDEX IF NOT EXISTS ix_engineering_worker_executions_lease_expiry
    ON engineering_worker_executions(lease_expires_at);

ALTER TABLE engineering_worker_executions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE engineering_worker_executions FROM anon, authenticated;

-- Worker lease/checkpoint state is server-owned control-plane data. Historical
-- EngineeringAttempt evidence remains append-only in its existing table; this
-- record only governs live ownership, recovery and bounded checkpoint state.

COMMIT;
