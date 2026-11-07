-- ===========================================================================
-- HydroCast Panchganga - Database Schema
-- Part 01: Core Tables (subbasins, gauge_stations, bridge_sites)
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

-- 2. Subbasins (Official Panchganga Delineation, Total Area: 1,837.213 km²)
CREATE TABLE IF NOT EXISTS subbasins (
    subbasin_id         VARCHAR(32) PRIMARY KEY,
    subbasin_name       VARCHAR(100) NOT NULL,
    drainage_area_km2   NUMERIC(8,3) NOT NULL,
    primary_station_id  VARCHAR(64) NOT NULL,
    centroid_lat        NUMERIC(8,4) NOT NULL,
    centroid_lon        NUMERIC(8,4) NOT NULL,
    tributary_stream    VARCHAR(100) NOT NULL,
    curve_number_amc3   NUMERIC(4,1) DEFAULT 88.0,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Gauge Stations (Full 20 Primary & Alternate Rain Gauge Network)
CREATE TABLE IF NOT EXISTS gauge_stations (
    station_id          VARCHAR(64) PRIMARY KEY,
    station_name        VARCHAR(100) NOT NULL,
    subbasin_id         VARCHAR(32) NOT NULL REFERENCES subbasins(subbasin_id) ON DELETE CASCADE,
    latitude            DOUBLE PRECISION NOT NULL,
    longitude           DOUBLE PRECISION NOT NULL,
    elevation_m         NUMERIC(6,1),
    is_primary          BOOLEAN DEFAULT TRUE,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gs_subbasin ON gauge_stations (subbasin_id);

-- 4. Bridge Sites (River Flood Monitoring & Warning Datums)
CREATE TABLE IF NOT EXISTS bridge_sites (
    site_id             VARCHAR(50) PRIMARY KEY,
    site_name           VARCHAR(100) NOT NULL,
    latitude            DOUBLE PRECISION NOT NULL,
    longitude           DOUBLE PRECISION NOT NULL,
    river_name          VARCHAR(100) DEFAULT 'Panchganga',
    alert_stage_m       NUMERIC(6,2) NOT NULL,
    warning_stage_m     NUMERIC(6,2) NOT NULL,
    danger_stage_m      NUMERIC(6,2) NOT NULL,
    hfl_m               NUMERIC(6,2) NOT NULL,
    bed_slope           NUMERIC(8,6) NOT NULL,
    zero_datum_m        NUMERIC(6,2) NOT NULL DEFAULT 530.18,
    sensor_datum_m      NUMERIC(6,2) DEFAULT 549.35,
    manning_n_bed       NUMERIC(4,3) DEFAULT 0.035,
    manning_n_floodplain NUMERIC(4,3) DEFAULT 0.070,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);