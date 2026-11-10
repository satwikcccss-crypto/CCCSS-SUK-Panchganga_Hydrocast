import re
with open('E:\\Hydrocast Windows Server\\frontend-admin\\components\\charts\\HydrographChart.tsx', 'r') as f:
    content = f.read()
patterns = ['terminal', 'logs', 'live', 'get_live', 'health_log']
for p in patterns:
    matches = [(m.start(), m.group()) for m in re.finditer(p, content, re.IGNORECASE)]
    if matches:
        print(f'Pattern "{p}": found {len(matches)} times')
        for pos, match in matches[:3]:
            print(f'  pos {pos}: {match}')
    else:
        print(f'Pattern "{p}": not found')