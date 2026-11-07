-- ===========================================================================
-- HydroCast Panchganga - Database Schema
-- Part 02: Simulation Runs (Computation Cycle Master Ledger)
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id                      VARCHAR(100) PRIMARY KEY,
    cycle_date                  DATE NOT NULL DEFAULT CURRENT_DATE,
    cycle_time                  VARCHAR(32) NOT NULL DEFAULT '00z',
    start_time                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time                    TIMESTAMPTZ,
    status                      VARCHAR(32) NOT NULL DEFAULT 'completed',
    model_version               VARCHAR(64) DEFAULT 'HEC-HMS-4.13',
    peak_discharge_m3s          NUMERIC(10,2),
    peak_stage_m                NUMERIC(6,2),
    lead_hours_to_peak          SMALLINT,
    total_volume_mcm            NUMERIC(10,2),
    total_rainfall_mm           NUMERIC(8,2),
    total_rainfall_volume_mcm   NUMERIC(10,2),
    alert_level                 VARCHAR(32) DEFAULT 'NORMAL',
    spearman_rho                NUMERIC(6,4),
    nse_score                   NUMERIC(6,4),
    error_message               TEXT,
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sim_runs_date ON simulation_runs (cycle_date DESC, start_time DESC);