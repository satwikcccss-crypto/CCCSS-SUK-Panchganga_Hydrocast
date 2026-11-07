-- ===========================================================================
-- HydroCast Panchganga - Database Storage Setup
-- Part 01: Dedicated Tablespace
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- Drive: E:\ (3512 GB dedicated tablespace for simulation data)
-- ===========================================================================

-- Create the dedicated tablespace on E:\ drive
-- 3512 GB allocation for simulation runs, hydrographs, metrics, and logs
CREATE TABLESPACE hydrocast_ts
    OWNER = hms_app
    LOCATION 'E:/pg_tablespace/hydrocast_ts';

-- Set the default tablespace for the rainfall_runoff database
ALTER DATABASE rainfall_runoff SET default_tablespace = hydrocast_ts;

-- Set default tablespace for current session
SET default_tablespace = hydrocast_ts;

-- Verify tablespace creation
SELECT spcname, pg_location_spcpath(spcname) AS path, pg_size_pretty(pg_tablespace_size(spcname)) AS size
FROM pg_tablespace
WHERE spcname = 'hydrocast_ts';

-- ===========================================================================
-- Note: This file is executed on the production PostgreSQL server at SUK.
-- The E:\ drive must be pre-formatted and accessible by the PostgreSQL
-- service account before running this script.
-- ===========================================================================