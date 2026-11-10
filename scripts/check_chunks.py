import urllib.request
import re

url = "http://localhost:3000/dashboard"
try:
    resp = urllib.request.urlopen(url)
    html = resp.read().decode("utf-8")
    scripts = re.findall(r'src="(/_next/static/[^"]+)"', html)
    print(f"Total script chunks in HTML: {len(scripts)}")
    for s in scripts:
        chunk_url = f"http://localhost:3000{s}"
        try:
            r = urllib.request.urlopen(chunk_url)
            print(f"  {s} -> {r.status} OK")
        except Exception as e:
            print(f"  {s} -> FAILED: {e}")
except Exception as e:
    print(f"Failed to access /dashboard: {e}")
