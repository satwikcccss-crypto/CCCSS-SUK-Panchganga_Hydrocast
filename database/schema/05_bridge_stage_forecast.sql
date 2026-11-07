-- ===========================================================================
-- HydroCast Panchganga - Database Schema
-- Part 05: Bridge Stage Forecast (90-Hour Forward Water Level Time Series)
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS bridge_stage_forecast (
    id                  BIGSERIAL PRIMARY KEY,
    site_id             VARCHAR(50) NOT NULL REFERENCES bridge_sites(site_id) ON DELETE CASCADE,
    forecast_run_id     VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    forecast_time       TIMESTAMPTZ NOT NULL,
    lead_hours          SMALLINT NOT NULL,
    discharge_m3s       NUMERIC(10,2) NOT NULL,
    stage_m             NUMERIC(6,2) NOT NULL,
    alert_level         VARCHAR(32) NOT NULL CHECK (alert_level IN ('NORMAL','ALERT','WARNING','DANGER','HFL_EXCEEDED')),
    is_above_danger     BOOLEAN DEFAULT FALSE,
    arrival_time        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bsf_site_run ON bridge_stage_forecast (site_id, forecast_run_id);