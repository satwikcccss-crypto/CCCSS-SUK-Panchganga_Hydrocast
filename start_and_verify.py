import subprocess, time, json, urllib.request, sys

# Start the server
proc = subprocess.Popen(
    [sys.executable, '-m', 'uvicorn', 'backend.api.main:app', '--host', '0.0.0.0', '--port', '8000'],
    cwd=r'E:\Hydrocast Windows Server',
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

# Wait for startup
time.sleep(3)

# Run verification
try:
    checks = {}

    # 1. Status
    try:
        with urllib.request.urlopen('http://localhost:8000/api/v1/status') as r:
            d = json.loads(r.read())
        checks['/api/v1/status'] = d.get('pipeline_ok')
    except: checks['/api/v1/status'] = 'ERR'

    # 2. Runoff summary
    try:
        with urllib.request.urlopen('http://localhost:8000/api/v1/runoff/summary') as r:
            d = json.loads(r.read())
        b0, b1 = d['bridges'][0], d['bridges'][1]
        checks['/api/v1/runoff/summary'] = f'Shivaji cur={b0["current_stage_m"]} peak={b0["peak_stage_m"]}; Rajaram cur={b1["current_stage_m"]} peak={b1["peak_stage_m"]}'
    except: checks['/api/v1/runoff/summary'] = 'ERR'

    # 3. Rainfall ECMWF
    try:
        with urllib.request.urlopen('http://localhost:8000/api/v1/rainfall/ecmwf') as r:
            d = json.loads(r.read())
        checks['/api/v1/rainfall/ecmwf'] = f'{len(d)} subbasins'
    except: checks['/api/v1/rainfall/ecmwf'] = 'ERR'

    # 4. Bridge stage Shivaji
    try:
        with urllib.request.urlopen('http://localhost:8000/api/v1/runoff/stage/SHIVAJI_BRIDGE') as r:
            d = json.loads(r.read())
        fc = d['forecast'][0]
        checks['/api/v1/runoff/stage/SHIVAJI'] = f'fc[0].stage_m={fc["stage_m"]}'
    except: checks['/api/v1/runoff/stage/SHIVAJI'] = 'ERR'

    # 5. Bridge stage Rajaram
    try:
        with urllib.request.urlopen('http://localhost:8000/api/v1/runoff/stage/RAJARAM_BRIDGE') as r:
            d = json.loads(r.read())
        fc = d['forecast'][0]
        checks['/api/v1/runoff/stage/RAJARAM'] = f'fc[0].stage_m={fc["stage_m"]}'
    except: checks['/api/v1/runoff/stage/RAJARAM'] = 'ERR'

    print('=== VERIFICATION RESULTS ===')
    for k, v in checks.items():
        print(f'  {k}: {v}')

    # Summary
    all_ok = all(isinstance(v, (int, float, str)) and str(v) != 'ERR' for v in checks.values())
    print()
    if all_ok:
        print('=== ALL CHECKS PASSED ===')
    else:
        print('=== SOME CHECKS FAILED ===')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()

# Kill the server
proc.terminate()
proc.wait()