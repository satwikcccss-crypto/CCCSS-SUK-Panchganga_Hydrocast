-- ===========================================================================
-- HydroCast Panchganga - Database Schema
-- Part 03: Forecast Validation Metrics (RMSE, NSE, Spearman, PBIAS Accuracy Matrix)
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS forecast_validation_metrics (
    id                          BIGSERIAL PRIMARY KEY,
    run_id                      VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    spearman_rho                NUMERIC(6,4) NOT NULL,
    spearman_rho_q              NUMERIC(6,4) NOT NULL,
    pearson_r2                  NUMERIC(6,4) NOT NULL,
    nse_stage                   NUMERIC(6,4) NOT NULL,
    nse_discharge               NUMERIC(6,4) NOT NULL,
    rmse_stage_m                NUMERIC(6,4) NOT NULL,
    mae_stage_m                 NUMERIC(6,4) NOT NULL,
    rmse_q_m3s                  NUMERIC(8,2),
    mae_q_m3s                   NUMERIC(8,2),
    pbias_stage_pct             NUMERIC(6,2) NOT NULL,
    pbias_discharge_pct         NUMERIC(6,2),
    basin_rainfall_accuracy_pct NUMERIC(5,2) NOT NULL,
    performance_grade           VARCHAR(32) DEFAULT 'EXCELLENT',
    sample_size_hours           SMALLINT DEFAULT 48,
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (run_id)
);

CREATE INDEX IF NOT EXISTS idx_fvm_run ON forecast_validation_metrics (run_id);