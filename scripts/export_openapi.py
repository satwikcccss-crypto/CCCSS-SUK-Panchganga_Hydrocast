#!/usr/bin/env python3
"""Export HydroCast OpenAPI schema for client/SDK generation.

Usage:
  python scripts/export_openapi.py --out openapi.json
  python scripts/export_openapi.py --app admin --out openapi-admin.json

This script imports the FastAPI app and writes its OpenAPI schema. It does not
start a server. Run from the repository root in an environment where backend
dependencies are installed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_app(which: str):
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if which == "admin":
        from backend.api.admin_app import app
    else:
        from backend.api.main import app
    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Export HydroCast OpenAPI schema")
    parser.add_argument("--app", choices=["public", "admin"], default="public", help="Which FastAPI app to export")
    parser.add_argument("--out", default="openapi.json", help="Output JSON file path")
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation")
    args = parser.parse_args()

    app = load_app(args.app)
    schema = app.openapi()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(schema, indent=args.indent, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.app} OpenAPI schema: {out_path} ({len(schema.get('paths', {}))} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
