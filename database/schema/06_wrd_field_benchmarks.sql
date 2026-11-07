-- ===========================================================================
-- HydroCast Panchganga - Database Schema
-- Part 06: WRD Official Rating Benchmarks
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS wrd_field_benchmarks (
    record_id           SERIAL PRIMARY KEY,
    stage_m             NUMERIC(6,2) NOT NULL,
    stage_feet_inches   VARCHAR(32) NOT NULL,
    discharge_cusecs    NUMERIC(10,1) NOT NULL,
    discharge_m3s       NUMERIC(10,2) NOT NULL,
    source_agency       VARCHAR(100) DEFAULT 'Maharashtra Water Resources Dept (WRD)',
    is_danger_threshold BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);