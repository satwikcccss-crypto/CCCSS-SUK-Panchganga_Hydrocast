#!/usr/bin/env python3
"""
Sync Community Standards files (.github/ISSUE_TEMPLATE/, PULL_REQUEST_TEMPLATE.md, ACCESSIBILITY.md)
directly to the default branch (main) on GitHub so the Community Standards checklist turns 100% GREEN.
Committer identity is read from environment variables. Udupi <[CONTACT_REDACTED]>.
"""

import base64
import json
import os
import sys
import urllib.request
import urllib.error

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
token = None
repo_owner = "satwikcccss-crypto"
repo_name = "CCCSS-SUK-Panchganga_Hydrocast"

if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("GITHUB_PAT="):
                token = line.split("=", 1)[1].strip()
            elif line.startswith("GITHUB_REPO_OWNER="):
                repo_owner = line.split("=", 1)[1].strip()
            elif line.startswith("GITHUB_REPO_NAME="):
                repo_name = line.split("=", 1)[1].strip()

if not token:
    print("ERROR: GITHUB_PAT not found in .env")
    sys.exit(1)

BASE_URL = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
HEADERS = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "HydroCast-Community-Sync/1.0",
    "X-GitHub-Api-Version": "2022-11-28",
}

COMMITTER = {
    "name": os.environ.get("GIT_AUTHOR_NAME", "HydroCast Maintainers"),
    "email": os.environ.get("GIT_AUTHOR_EMAIL", "")
}

def get_file_sha(path, branch="main"):
    url = f"{BASE_URL}/contents/{path}?ref={branch}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print(f"Error fetching SHA for {path}: {e}")
        return None
    except Exception as e:
        print(f"Error fetching SHA for {path}: {e}")
        return None

def put_file(local_path, remote_path, message, branch="main"):
    with open(local_path, "rb") as f:
        content_bytes = f.read()
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
    sha = get_file_sha(remote_path, branch)

    payload = {
        "message": message,
        "content": content_b64,
        "branch": branch,
        "committer": COMMITTER,
        "author": COMMITTER,
    }
    if sha:
        payload["sha"] = sha

    url = f"{BASE_URL}/contents/{remote_path}"
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=HEADERS, method="PUT")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            action = "Updated" if sha else "Created"
            print(f"  ✓ {action} {remote_path} on branch {branch}")
            return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        print(f"  ✗ Failed to put {remote_path}: HTTP {e.code} - {err_msg}")
        return False
    except Exception as e:
        print(f"  ✗ Failed to put {remote_path}: {e}")
        return False

# Files to sync
FILES_TO_SYNC = [
    ("ACCESSIBILITY.md", "ACCESSIBILITY.md"),
    (".github/ACCESSIBILITY.md", ".github/ACCESSIBILITY.md"),
    (".github/ISSUE_TEMPLATE.md", ".github/ISSUE_TEMPLATE.md"),
    (".github/issue_template.md", ".github/issue_template.md"),
    (".github/PULL_REQUEST_TEMPLATE.md", ".github/PULL_REQUEST_TEMPLATE.md"),
    (".github/pull_request_template.md", ".github/pull_request_template.md"),
    (".github/ISSUE_TEMPLATE/config.yml", ".github/ISSUE_TEMPLATE/config.yml"),
    (".github/ISSUE_TEMPLATE/README.md", ".github/ISSUE_TEMPLATE/README.md"),
    (".github/ISSUE_TEMPLATE/01_bug_report.md", ".github/ISSUE_TEMPLATE/01_bug_report.md"),
    (".github/ISSUE_TEMPLATE/02_feature_request.md", ".github/ISSUE_TEMPLATE/02_feature_request.md"),
    (".github/ISSUE_TEMPLATE/03_sensor_telemetry_incident.md", ".github/ISSUE_TEMPLATE/03_sensor_telemetry_incident.md"),
    (".github/ISSUE_TEMPLATE/04_hydrology_recalibration.md", ".github/ISSUE_TEMPLATE/04_hydrology_recalibration.md"),
    (".github/ISSUE_TEMPLATE/05_security_incident.md", ".github/ISSUE_TEMPLATE/05_security_incident.md"),
    ("ISSUES.md", "ISSUES.md"),
]

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print(f"Syncing Community Standards files to GitHub repo '{repo_owner}/{repo_name}' on branch 'main'...")

for local_rel, remote_path in FILES_TO_SYNC:
    local_abs = os.path.join(root_dir, local_rel)
    if os.path.exists(local_abs):
        msg = f"docs(community): sync {remote_path} for GitHub community standards benchmark"
        put_file(local_abs, remote_path, msg, branch="main")
    else:
        print(f"  ! Local file not found: {local_abs}")

print("\nVerifying Community Profile on GitHub...")
try:
    req = urllib.request.Request(f"{BASE_URL}/community/profile", headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        profile = json.loads(resp.read().decode("utf-8"))
        print(f"Health percentage: {profile.get('health_percentage')}%")
        print("Files status:")
        for k, v in profile.get("files", {}).items():
            status = "✓ PRESENT" if v else "✗ MISSING"
            print(f"  - {k}: {status}")
except Exception as e:
    print(f"Error fetching profile: {e}")
