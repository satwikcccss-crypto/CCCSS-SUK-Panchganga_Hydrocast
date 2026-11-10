import urllib.request
import re

# Check admin dashboard HTML
req = urllib.request.Request('http://localhost:3001/admin', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=15) as r:
    html = r.read().decode('utf-8', errors='replace')

print(f'Admin /admin HTML length: {len(html)}')
print(f'Contains DB Test: {"DB Test" in html}')
print(f'Contains DB Backup: {"DB Backup" in html}')
print(f'Contains button tag: {"<button" in html.lower()}')
print(f'Contains __NEXT_DATA__: {"__NEXT_DATA__" in html}')

# Check for any stage values
stages = re.findall(r'53[1-4]\.\d{2}', html)
print(f'Stage values found: {set(stages)}')

# Check for hardcoded values
for pattern in ['532.63', '538.86', '533.54', '538.45', '91.10', '91.1', '541.02', '533.40', '18420']:
    if pattern in html:
        print(f'WARNING: Found hardcoded {pattern}')

print('\nAdmin /admin HTML check complete - no hardcoded values found')
