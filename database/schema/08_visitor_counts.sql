-- ===========================================================================
-- HydroCast Panchganga - Database Schema
-- Part 08: Visitor Analytics (Public Website Counter)
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS visitor_counts (
    visit_date          DATE PRIMARY KEY DEFAULT CURRENT_DATE,
    unique_visitors     INTEGER NOT NULL DEFAULT 1,
    total_pageviews     INTEGER NOT NULL DEFAULT 1,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);