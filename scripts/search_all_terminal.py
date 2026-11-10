import os, re

base = "E:\\Hydrocast Windows Server\\frontend-admin\\components"
patterns = ['terminal', 'logs', 'live', 'get_live', 'health_log', 'terminal_log', 'live_log']

for root, dirs, files in os.walk(base):
    # Skip node_modules and .next
    if 'node_modules' in root or '.next' in root:
        continue
    for fname in files:
        if not fname.endswith('.tsx'):
            continue
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except:
            continue
        
        for p in patterns:
            matches = [(m.start(), m.group()) for m in re.finditer(p, content, re.IGNORECASE)]
            if matches:
                print(f"{fpath} - {p}: {len(matches)} matches")
                for pos, match in matches[:2]:
                    # Show context
                    start = max(0, pos - 50)
                    end = min(len(content), pos + 100)
                    ctx = content[start:end].replace('\n', ' ')
                    print(f"    pos {pos}: ...{ctx}...")