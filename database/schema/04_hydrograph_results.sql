-- ===========================================================================
-- HydroCast Panchganga - Database Schema
-- Part 04: Hydrograph Results (HEC-HMS 90-Hour Basin Outflow)
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS hydrograph_results (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    basin_id            VARCHAR(50) NOT NULL DEFAULT 'PANCHGANGA_BASIN',
    outlet_node         VARCHAR(50) NOT NULL DEFAULT 'J_Outlet',
    timestamp           TIMESTAMPTZ NOT NULL,
    lead_hours          SMALLINT NOT NULL,
    discharge_m3s       NUMERIC(10,2) NOT NULL,
    surface_runoff_m3s  NUMERIC(10,2) NOT NULL DEFAULT 0,
    baseflow_m3s        NUMERIC(10,2) NOT NULL DEFAULT 45.0,
    is_peak             BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hg_run_lead ON hydrograph_results (run_id, lead_hours);
CREATE INDEX IF NOT EXISTS idx_hg_timestamp ON hydrograph_results (timestamp DESC);