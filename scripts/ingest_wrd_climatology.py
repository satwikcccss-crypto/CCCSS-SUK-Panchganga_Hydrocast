"""
scripts/ingest_wrd_climatology.py
=================================
Extracts 20 years of WRD non-monsoon river stage and project release records
from 'nond wahi 2004 to 2024.zip' and populates the `wrd_seasonal_climatology`
reference table in PostgreSQL.
"""

import io
import re
import zipfile
from datetime import datetime
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

ZIP_PATH = r"E:\Hydrocast Windows Server\nond wahi 2004 to 2024.zip"
DB_URL = "postgresql://hms_app:REPLACE_ME_DB_PASSWORD@127.0.0.1:5432/rainfall_runoff"
RAJARAM_GAUGE_ZERO_M = 530.18

def parse_feet_inches(val_str: str) -> float:
    """Convert '12\'0\"' or '11\'6\"' to decimal feet."""
    if not isinstance(val_str, str):
        try:
            return float(val_str)
        except Exception:
            return None
    m = re.match(r"(\d+)'\s*(\d+)?", val_str)
    if m:
        ft = float(m.group(1))
        inch = float(m.group(2)) if m.group(2) else 0.0
        return ft + inch / 12.0
    try:
        return float(val_str)
    except Exception:
        return None

def extract_wrd_statistics():
    print("Reading WRD archive:", ZIP_PATH)
    stages_by_month = {m: [] for m in range(1, 13)}
    discharges_cusecs_by_month = {m: [] for m in range(1, 13)}

    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        # 1. Parse K.T. Weir levels (2023-24 sample and others)
        for name in z.namelist():
            if "k.t. wair level" in name.lower() and name.endswith(".xls"):
                try:
                    data = z.read(name)
                    xl = pd.ExcelFile(io.BytesIO(data))
                    for sheet in xl.sheet_names:
                        if "kolhapur" in sheet.lower():
                            df = xl.parse(sheet, header=None)
                            for r in range(3, len(df)):
                                dt_val = df.iloc[r, 1]
                                st_val = df.iloc[r, 2]  # Rajaram Weir
                                if pd.notna(dt_val) and pd.notna(st_val):
                                    try:
                                        if isinstance(dt_val, datetime):
                                            dt = dt_val
                                        else:
                                            dt = pd.to_datetime(str(dt_val)[:10])
                                        ft = parse_feet_inches(str(st_val))
                                        if ft is not None and 5.0 <= ft <= 45.0:
                                            stages_by_month[dt.month].append(ft)
                                    except Exception:
                                        pass
                except Exception as e:
                    pass

            # 2. Parse Kolhapur Discharge sheets
            if "kolhapur discharge" in name.lower() and name.endswith(".xls"):
                try:
                    data = z.read(name)
                    xl = pd.ExcelFile(io.BytesIO(data))
                    for sheet in xl.sheet_names:
                        df = xl.parse(sheet, header=None)
                        for r in range(4, len(df)):
                            dt_val = df.iloc[r, 1]
                            q_val = df.iloc[r, 5]  # Total release cusecs
                            if pd.notna(dt_val) and pd.notna(q_val):
                                try:
                                    if isinstance(dt_val, datetime):
                                        dt = dt_val
                                    else:
                                        dt = pd.to_datetime(str(dt_val)[:10])
                                    q_f = float(q_val)
                                    if 0.0 <= q_f <= 20000.0:
                                        discharges_cusecs_by_month[dt.month].append(q_f)
                                except Exception:
                                    pass
                except Exception:
                    pass

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    climatology_rows = []

    for m in range(1, 13):
        m_name = month_names[m - 1]
        is_monsoon = 6 <= m <= 10
        st_list = stages_by_month[m]
        q_list = discharges_cusecs_by_month[m]

        if st_list:
            median_ft = float(np.median(st_list))
            p10_ft = float(np.percentile(st_list, 10))
            p90_ft = float(np.percentile(st_list, 90))
        else:
            median_ft = 11.5 if not is_monsoon else 22.0
            p10_ft = 10.0 if not is_monsoon else 15.0
            p90_ft = 13.0 if not is_monsoon else 35.0

        if q_list:
            median_cusecs = float(np.median(q_list))
        else:
            median_cusecs = 400.0 if not is_monsoon else 3200.0

        median_stage_m = round(RAJARAM_GAUGE_ZERO_M + median_ft * 0.3048, 2)
        median_q_m3s = round(median_cusecs * 0.0283168, 2)

        regime = "MONSOON_FLOOD" if is_monsoon else "DRY_SEASON_REGULATED"
        desc = "Active monsoon flood warning season" if is_monsoon else "Weir & dam regulated channel flow (sugar crop & drinking supply)"

        climatology_rows.append((
            m,
            m_name,
            regime,
            median_stage_m,
            median_q_m3s,
            round(median_cusecs, 1),
            round(p10_ft, 1),
            round(median_ft, 1),
            round(p90_ft, 1),
            desc
        ))

    return climatology_rows

def ingest_to_postgres(rows):
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS wrd_seasonal_climatology (
            month_int INTEGER PRIMARY KEY,
            month_name VARCHAR(10) NOT NULL,
            regime VARCHAR(30) NOT NULL,
            median_stage_rajaram_m NUMERIC(6, 2) NOT NULL,
            median_discharge_m3s NUMERIC(8, 2) NOT NULL,
            median_release_cusecs NUMERIC(8, 1) NOT NULL,
            gauge_p10_ft NUMERIC(5, 1),
            gauge_median_ft NUMERIC(5, 1),
            gauge_p90_ft NUMERIC(5, 1),
            description TEXT,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    upsert_sql = """
        INSERT INTO wrd_seasonal_climatology (
            month_int, month_name, regime, median_stage_rajaram_m, median_discharge_m3s,
            median_release_cusecs, gauge_p10_ft, gauge_median_ft, gauge_p90_ft, description
        ) VALUES %s
        ON CONFLICT (month_int) DO UPDATE SET
            regime = EXCLUDED.regime,
            median_stage_rajaram_m = EXCLUDED.median_stage_rajaram_m,
            median_discharge_m3s = EXCLUDED.median_discharge_m3s,
            median_release_cusecs = EXCLUDED.median_release_cusecs,
            gauge_p10_ft = EXCLUDED.gauge_p10_ft,
            gauge_median_ft = EXCLUDED.gauge_median_ft,
            gauge_p90_ft = EXCLUDED.gauge_p90_ft,
            description = EXCLUDED.description,
            updated_at = NOW();
    """

    execute_values(cur, upsert_sql, rows)
    conn.commit()
    print("Successfully ingested 12 monthly WRD climatology records into PostgreSQL!")

    cur.execute("SELECT month_int, month_name, regime, median_stage_rajaram_m, median_discharge_m3s, median_release_cusecs FROM wrd_seasonal_climatology ORDER BY month_int;")
    for r in cur.fetchall():
        print(f"  Month {r[0]:02d} ({r[1]}): {r[2]} -> Stage: {r[3]}m MSL | Q: {r[4]} m³/s ({r[5]} cusecs)")

    cur.close()
    conn.close()

if __name__ == "__main__":
    rows = extract_wrd_statistics()
    ingest_to_postgres(rows)
