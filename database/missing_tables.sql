-- =============================================================================
-- Missing tables for full end-to-end pipeline
-- =============================================================================

-- ECMWF areal rainfall time series per subbasin
CREATE TABLE IF NOT EXISTS subbasin_rainfall_ts (
    id                  BIGSERIAL PRIMARY KEY,
    subbasin_id         VARCHAR(32) NOT NULL REFERENCES subbasins(subbasin_id),
    valid_time          TIMESTAMPTZ NOT NULL,
    lead_hours          SMALLINT NOT NULL,
    rainfall_mm_hr      NUMERIC(6,2) NOT NULL,
    source_id           VARCHAR(32) NOT NULL DEFAULT 'ecmwf_ifs',
    forecast_run_time   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_srt_subbasin_run ON subbasin_rainfall_ts (subbasin_id, forecast_run_time);
CREATE INDEX IF NOT EXISTS idx_srt_valid_time ON subbasin_rainfall_ts (valid_time);

-- Station selection decisions per cycle
CREATE TABLE IF NOT EXISTS station_selection_log (
    id                BIGSERIAL PRIMARY KEY,
    subbasin_id       VARCHAR(32) NOT NULL REFERENCES subbasins(subbasin_id),
    selected_station_id VARCHAR(64) NOT NULL,
    cumulative_mm     NUMERIC(8,2),
    all_candidates_json JSONB,
    selected_at       TIMESTAMPTZ DEFAULT NOW(),
    cycle_id          VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id)
);
CREATE INDEX IF NOT EXISTS idx_ssl_cycle ON station_selection_log (cycle_id);
CREATE INDEX IF NOT EXISTS idx_ssl_subbasin ON station_selection_log (subbasin_id);

-- Active flood alerts
CREATE TABLE IF NOT EXISTS alert_events (
    id              BIGSERIAL PRIMARY KEY,
    site_id         VARCHAR(50) NOT NULL REFERENCES bridge_sites(site_id),
    alert_level     VARCHAR(32) NOT NULL,
    stage_m         NUMERIC(6,2) NOT NULL,
    discharge_m3s   NUMERIC(10,2),
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          VARCHAR(32) NOT NULL DEFAULT 'active',
    message         TEXT,
    cancelled_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ae_site ON alert_events (site_id);
CREATE INDEX IF NOT EXISTS idx_ae_status ON alert_events (status);

-- Peak discharge events per run
CREATE TABLE IF NOT EXISTS peak_discharge_events (
    id              BIGSERIAL PRIMARY KEY,
    run_id          VARCHAR(100) NOT NULL REFERENCES simulation_runs(run_id),
    outlet_node     VARCHAR(50) NOT NULL DEFAULT 'J_Outlet',
    peak_discharge_m3s NUMERIC(10,2) NOT NULL,
    time_of_peak    TIMESTAMPTZ NOT NULL,
    total_runoff_volume_m3 NUMERIC(12,2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pde_run ON peak_discharge_events (run_id);

-- Verification
SELECT 'subbasin_rainfall_ts' as table_name, COUNT(*) as row_count FROM subbasin_rainfall_ts
UNION ALL SELECT 'station_selection_log', COUNT(*) FROM station_selection_log
UNION ALL SELECT 'alert_events', COUNT(*) FROM alert_events
UNION ALL SELECT 'peak_discharge_events', COUNT(*) FROM peak_discharge_events;
