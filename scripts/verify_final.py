import json, urllib.request

print('=== FINAL VERIFICATION ===')
print()

# 1. Status
try:
    with urllib.request.urlopen('http://localhost:8000/api/v1/status') as r:
        d = json.loads(r.read())
    polo = d.get('pipeline_ok')
    print(f'1. /api/v1/status: pipeline_ok={polo}')
except Exception as e:
    print(f'1. /api/v1/status: ERR {e}')

# 2. Runoff summary
try:
    with urllib.request.urlopen('http://localhost:8000/api/v1/runoff/summary') as r:
        d = json.loads(r.read())
    b0, b1 = d['bridges'][0], d['bridges'][1]
    print(f'2. /api/v1/runoff/summary:')
    print(f'   Shivaji: current={b0["current_stage_m"]} peak={b0["peak_stage_m"]}')
    print(f'   Rajaram: current={b1["current_stage_m"]} peak={b1["peak_stage_m"]}')
except Exception as e:
    print(f'2. /api/v1/runoff/summary: ERR {e}')

# 3. Rainfall ECMWF
try:
    with urllib.request.urlopen('http://localhost:8000/api/v1/rainfall/ecmwf') as r:
        d = json.loads(r.read())
    print(f'3. /api/v1/rainfall/ecmwf: {len(d)} subbasins live Open-Meteo')
except Exception as e:
    print(f'3. /api/v1/rainfall/ecmwf: ERR {e}')

# 4. Bridge stage Shivaji
try:
    with urllib.request.urlopen('http://localhost:8000/api/v1/runoff/stage/SHIVAJI_BRIDGE') as r:
        d = json.loads(r.read())
    fc = d['forecast'][0]
    print(f'4. /api/v1/runoff/stage/SHIVAJI: fc[0].stage_m={fc["stage_m"]} alerts: alert={d["site"]["alert_stage_m"]} warning={d["site"]["warning_stage_m"]} danger={d["site"]["danger_stage_m"]}')
except Exception as e:
    print(f'4. /api/v1/runoff/stage/SHIVAJI: ERR {e}')

# 5. Bridge stage Rajaram
try:
    with urllib.request.urlopen('http://localhost:8000/api/v1/runoff/stage/RAJARAM_BRIDGE') as r:
        d = json.loads(r.read())
    fc = d['forecast'][0]
    print(f'5. /api/v1/runoff/stage/RAJARAM: fc[0].stage_m={fc["stage_m"]} alerts: alert={d["site"]["alert_stage_m"]} warning={d["site"]["warning_stage_m"]} danger={d["site"]["danger_stage_m"]}')
except Exception as e:
    print(f'5. /api/v1/runoff/stage/RAJARAM: ERR {e}')

print()
print('=== VERIFICATION COMPLETE ===')