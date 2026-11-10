import json

with open('E:\\Hydrocast Windows Server\\comprehensive_frontend_audit.json', 'r') as f:
    r = json.load(f)

print('=== SUMMARY ===')
print(json.dumps(r['summary'], indent=2))

print('\n=== PUBLIC PAGES BUTTONS ===')
for path, pg in r['public_pages'].items():
    print(f'\n{path} (status {pg["status"]}):')
    for btn in pg['buttons']:
        print(f'  Button: text="{btn["text"][:50]}" type={btn["type"]} disabled={btn["disabled"]}')
    for inp in pg['inputs']:
        print(f'  Input: type={inp["type"]} name={inp["name"]} placeholder={inp["placeholder"][:50]}')
    for link in pg['links']:
        print(f'  Link: href={link["href"]} text={link["text"][:50]}')
    if pg['errors']:
        print(f'  Errors: {pg["errors"]}')

print('\n=== ADMIN PAGES BUTTONS ===')
for path, pg in r['admin_pages'].items():
    print(f'\n{path} (status {pg["status"]}):')
    for btn in pg['buttons']:
        print(f'  Button: text="{btn["text"][:50]}" type={btn["type"]} disabled={btn["disabled"]}')
    for inp in pg['inputs']:
        print(f'  Input: type={inp["type"]} name={inp["name"]} placeholder={inp["placeholder"][:50]}')
    for link in pg['links']:
        print(f'  Link: href={link["href"]} text={link["text"][:50]}')
    if pg['errors']:
        print(f'  Errors: {pg["errors"]}')

print('\n=== API ENDPOINTS ===')
for ep, info in r['api_endpoints'].items():
    print(f'  {ep}: {info["status"]} OK={info["ok"]}')

print('\n=== HARDCODED FINDINGS ===')
found_any = False
for pg_name, pg_data in list(r['public_pages'].items()) + list(r['admin_pages'].items()):
    for hf in pg_data.get('hardcoded_findings', []):
        found_any = True
        print(f'  [{pg_name}] {hf["description"]} in {hf["source"]}')
        for m in hf.get('matches', [])[:3]:
            print(f'    Match: "{m}"')
if not found_any:
    print("  None found - all clean!")
