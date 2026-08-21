-- P2-V0.8.0 — bind new engineering runs to exact approved Work Specification revisions.
-- Nullable columns preserve historical pre-v0.8 engineering-run readability.

ALTER TABLE engineering_runs
    ADD COLUMN IF NOT EXISTS work_specification_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS work_specification_revision INTEGER,
    ADD COLUMN IF NOT EXISTS work_specification_digest VARCHAR(64);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_engineering_runs_work_specification'
    ) THEN
        ALTER TABLE engineering_runs
            ADD CONSTRAINT fk_engineering_runs_work_specification
            FOREIGN KEY (work_specification_id)
            REFERENCES work_specifications(id)
            ON DELETE RESTRICT;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS ix_engineering_runs_work_specification_id
    ON engineering_runs(work_specification_id);
