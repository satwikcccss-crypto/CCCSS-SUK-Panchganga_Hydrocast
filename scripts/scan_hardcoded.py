import os, re

# Search for hardcoded numeric fallbacks in frontend code
base_dirs = [
    "E:\\Hydrocast Windows Server\\frontend-public",
    "E:\\Hydrocast Windows Server\\frontend-admin",
]

for base_dir in base_dirs:
    print(f"\n{'='*60}")
    print(f"SCANNING: {base_dir}")
    print(f"{'='*60}")
    
    for root, dirs, files in os.walk(base_dir):
        if 'node_modules' in root or '.next' in root:
            continue
        for f in files:
            if not f.endswith(('.tsx', '.ts', '.js', '.jsx')):
                continue
            fpath = os.path.join(root, f)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as fh:
                    content = fh.read()
            except:
                continue
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith('//') or stripped.startswith('*'):
                    continue
                
                # Check for ?? number fallbacks
                for m in re.finditer(r'\?\?\s*(\d+(?:\.\d+)?)', line):
                    val = m.group(1)
                    # Skip 0 and 1 which are often legitimate defaults
                    if float(val) in (0, 1, 0.0, 1.0):
                        continue
                    print(f"  {os.path.relpath(fpath, base_dir)}:{i+1}: ?? {val}  <- {stripped[:100]}")
                
                # Check for = number.number patterns (potential hardcoded thresholds)
                for m in re.finditer(r'(alert|warning|danger|hfl|stage_m|peak_stage|current_stage)\s*=\s*\d+\.\d+', line, re.IGNORECASE):
                    val = m.group(0)
                    print(f"  {os.path.relpath(fpath, base_dir)}:{i+1}: {val[:100]}  <- {stripped[:100]}")
