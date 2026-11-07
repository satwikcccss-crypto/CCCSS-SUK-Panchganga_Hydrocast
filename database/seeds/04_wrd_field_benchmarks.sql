-- ===========================================================================
-- HydroCast Panchganga - Seed Data
-- Part 04: WRD Official Field Gauge Rating Benchmarks
-- Target: PostgreSQL 16 + PostGIS on Windows Server Standard (SUK)
-- ===========================================================================

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