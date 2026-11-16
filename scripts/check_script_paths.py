import os
import re
from pathlib import Path

scripts_dir = str(Path(__file__).resolve().parent)
issues = []

for f in os.listdir(scripts_dir):
    if not f.endswith(".py"):
        continue
    filepath = os.path.join(scripts_dir, f)
    with open(filepath, "r", errors="replace") as fh:
        content = fh.read()
    # Look for relative path references to project root directories
    patterns = [
        r"open\(['\"](\.\./)?(data|backend|database|frontend|docs|config|logs|reports)",
        r"Path\(['\"](\.\./)?(data|backend|database|frontend|docs|config|logs|reports)",
        r"['\"](\.\./)?(data|backend|database|frontend|docs|config|logs|reports)/",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content)
        if matches:
            issues.append((f, matches[:3]))

if issues:
    print("POTENTIAL PATH ISSUES:")
    for fname, matches in issues:
        print(f"  {fname}: {matches}")
else:
    print("No path issues found - all scripts use absolute paths or project-root references")