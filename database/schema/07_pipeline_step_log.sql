-- ===========================================================================
-- HydroCast Panchganga - Database Schema
-- Part 07: Pipeline Step Execution Telemetry Log
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS pipeline_step_log (
    cycle_id            VARCHAR(100) NOT NULL,
    step_number         SMALLINT NOT NULL,
    step_name           VARCHAR(256) NOT NULL,
    status              VARCHAR(32) NOT NULL DEFAULT 'running',
    start_time          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time            TIMESTAMPTZ,
    duration_seconds    NUMERIC(10,2),
    details_json        JSONB,
    error_message       TEXT,
    PRIMARY KEY (cycle_id, step_number)
);

CREATE INDEX IF NOT EXISTS idx_psl_cycle ON pipeline_step_log (cycle_id);