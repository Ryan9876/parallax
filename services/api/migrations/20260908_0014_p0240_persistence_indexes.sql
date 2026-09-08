BEGIN;

-- P2-V0.24.0 adds only read-path indexes. No table or row is rewritten.
CREATE INDEX IF NOT EXISTS ix_engineering_runs_conversation_updated
    ON engineering_runs(conversation_id, updated_at DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_engineering_runs_binding_updated
    ON engineering_runs(conversation_id, work_specification_id, updated_at DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_engineering_runs_project_updated
    ON engineering_runs(project_id, updated_at DESC, created_at DESC, id);
CREATE INDEX IF NOT EXISTS ix_engineering_attempts_run_status_stage
    ON engineering_attempts(run_id, status, stage);

COMMIT;
