-- ===========================================================================
-- HydroCast Panchganga Official Seed Data
-- Shivaji University Kolhapur (SUK) Catchment Model
-- ===========================================================================

-- 1. Seed Subbasins S1 to S9
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

-- 2. Seed 20 Primary and Alternate Rain Gauge Stations
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

-- 3. Seed Bridge Sites
INSERT INTO bridge_sites (site_id, site_name, latitude, longitude,
    alert_stage_m, warning_stage_m, danger_stage_m, hfl_m,
    bed_slope, zero_datum_m, sensor_datum_m)
VALUES
    ('SHIVAJI_BRIDGE', 'Chhatrapati Shivaji Maharaj Bridge (Panchganga Ghat)', 16.708917, 74.219278,
     542.10, 542.70, 543.30, 545.33, 0.005858, 530.18, 549.35),
    ('RAJARAM_BRIDGE', 'Rajaram K.T. Weir (Kasba Bawada)', 16.736167, 74.235889,
     541.50, 542.07, 543.30, 545.33, 0.002318, 530.18, 548.90)
ON CONFLICT (site_id) DO UPDATE SET
    alert_stage_m = EXCLUDED.alert_stage_m,
    warning_stage_m = EXCLUDED.warning_stage_m,
    danger_stage_m = EXCLUDED.danger_stage_m,
    hfl_m = EXCLUDED.hfl_m;

-- 4. Seed WRD Official Field Gauge Rating Benchmarks
INSERT INTO wrd_field_benchmarks (stage_m, stage_feet_inches, discharge_cusecs, discharge_m3s, is_danger_threshold)
VALUES
    (533.54, '11''.0"',  2825.0,   80.0, FALSE),
    (533.56, '11''.1"',  2869.0,   81.2, FALSE),
    (533.59, '11''.2"',  2913.0,   82.5, FALSE),
    (533.64, '11''.4"',  3002.0,   85.0, FALSE),
    (533.66, '11''.5"',  3046.0,   86.3, FALSE),
    (533.69, '11''.6"',  3090.0,   87.5, FALSE),
    (533.71, '11''.7"',  3134.0,   88.7, FALSE),
    (533.99, '12''.6"',  3902.0,  110.5, FALSE),
    (535.21, '16''.6"',  7684.0,  217.6, FALSE),
    (535.59, '17''.9"',  8958.0,  253.7, FALSE),
    (535.77, '18''.4"',  9690.0,  274.4, FALSE),
    (536.41, '20''.5"', 13087.0,  370.6, FALSE),
    (538.16, '26''.2"', 21650.0,  613.1, FALSE),
    (539.02, '29''.0"', 28270.0,  800.5, FALSE),
    (540.00, '32''.2"', 38000.0, 1076.0, FALSE),
    (542.10, '39''.1"', 58000.0, 1642.4, FALSE), -- Alert Level
    (542.70, '41''.1"', 72000.0, 2038.8, FALSE), -- Warning Level
    (543.30, '43''.0"', 94500.0, 2675.9, TRUE),  -- Danger Level
    (545.33, '49''.8"',136000.0, 3851.1, TRUE)   -- HFL
ON CONFLICT DO NOTHING;

