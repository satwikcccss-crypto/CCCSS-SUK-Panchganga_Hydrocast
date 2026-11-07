-- ===========================================================================
-- HydroCast Panchganga - Seed Data
-- Part 02: Gauge Stations (Full 20 Primary & Alternate Rain Gauge Network)
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

INSERT INTO gauge_stations (station_id, station_name, subbasin_id, latitude, longitude, elevation_m, is_primary)
VALUES
    ('KARVEER', 'Karveer', 'S1', 16.706369, 74.2481772, 550.0, TRUE),
    ('SANGARUL', 'Sangarul', 'S2', 16.6841962, 74.0931627, 572.0, TRUE),
    ('BALINGA', 'Balinga', 'S2', 16.6878443, 74.17031, 560.0, FALSE),
    ('KALE', 'Kale', 'S2', 16.7228087, 74.0564499, 580.0, FALSE),
    ('KOTOLI', 'Kotoli', 'S3', 16.7820174, 74.0518705, 585.0, TRUE),
    ('BAJAR_BHOGAON', 'Bajar Bhogaon', 'S3', 16.8086769, 74.1107824, 590.0, FALSE),
    ('PADAL', 'Padal', 'S3', 16.7446006, 74.115187, 575.0, FALSE),
    ('KARANJPHEN', 'Karanjphen', 'S4', 16.7850973, 73.9036487, 640.0, TRUE),
    ('PADASALI', 'Padasali', 'S5', 16.701934, 73.843584, 620.0, TRUE),
    ('SALWAN', 'Salwan', 'S5', 16.6712, 73.9735, 595.0, FALSE),
    ('GAGANBAWDA', 'Gaganbawda', 'S6', 16.5469926, 73.8346738, 680.0, TRUE),
    ('GARIVADE', 'Garivade', 'S7', 16.520366, 73.918419, 610.0, TRUE),
    ('BEED', 'Beed', 'S8', 16.647984, 74.1288964, 565.0, TRUE),
    ('SHIROLI_DHUMALA', 'Shiroli-Dhumala', 'S8', 16.6166768, 74.1062828, 560.0, FALSE),
    ('RADHANAGARI', 'Radhanagari', 'S9', 16.41021, 73.9971822, 615.0, TRUE),
    ('HALADI', 'Haladi', 'S9', 16.5932632, 74.156292, 555.0, FALSE),
    ('RASHIWADE_BK', 'Rashiwade Bk.', 'S9', 16.5475641, 74.1019728, 570.0, FALSE),
    ('AAVALI_BK', 'Aavali Bk.', 'S9', 16.481009, 74.0549812, 585.0, FALSE),
    ('KASABA_TARALE', 'Kasaba Tarale', 'S9', 16.4478876, 74.021589, 595.0, FALSE),
    ('KASABA_WALAWE', 'Kasaba Walawe', 'S9', 16.41021, 73.9971822, 615.0, FALSE)
ON CONFLICT (station_id) DO UPDATE SET
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    elevation_m = EXCLUDED.elevation_m;