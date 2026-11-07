-- ===========================================================================
-- HydroCast Panchganga - Seed Data
-- Part 01: Subbasins S1 to S9
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

INSERT INTO subbasins (subbasin_id, subbasin_name, drainage_area_km2, primary_station_id, centroid_lat, centroid_lon, tributary_stream)
VALUES
    ('S1', 'Karveer (Outlet Reach)',       86.213, 'KARVEER',     16.7064, 74.2482, 'Panchganga Mainstem'),
    ('S2', 'Sangarul (Tulsi Lower)',      153.770, 'SANGARUL',    16.6842, 74.0932, 'Tulsi River'),
    ('S3', 'Kotoli (Kasari Lower)',       261.320, 'KOTOLI',      16.7820, 74.0519, 'Kasari River'),
    ('S4', 'Karanjphen (Kasari Headwater)',262.000,'KARANJPHEN',  16.7851, 73.9036, 'Kasari River'),
    ('S5', 'Padasali (Kumbhi Basin)',     106.390, 'PADASALI',    16.7019, 73.8436, 'Kumbhi River'),
    ('S6', 'Gaganbawda (Crest Reach)',    227.720, 'GAGANBAWDA',  16.5470, 73.8347, 'Dhamani River'),
    ('S7', 'Garivade (Ridge Catchment)',  195.390, 'GARIVADE',    16.5204, 73.9184, 'Dhamani/Bhogawati Divide'),
    ('S8', 'Beed (Bhogawati Mid-reach)',  177.440, 'BEED',        16.6480, 74.1289, 'Bhogawati River'),
    ('S9', 'Radhanagari (Upper Catchment)',366.970,'RADHANAGARI', 16.4102, 73.9972, 'Bhogawati River')
ON CONFLICT (subbasin_id) DO UPDATE SET
    drainage_area_km2 = EXCLUDED.drainage_area_km2,
    primary_station_id = EXCLUDED.primary_station_id,
    centroid_lat = EXCLUDED.centroid_lat,
    centroid_lon = EXCLUDED.centroid_lon;