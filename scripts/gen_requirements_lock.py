"""
scripts/gen_requirements_lock.py
================================
Generate ``requirements.lock`` — the exact versions of the project's DIRECT
runtime dependencies as installed in the validated environment.

Why a "direct" lock rather than a full ``pip freeze``: the developer machine has
321 packages (Jupyter, widgets, unrelated tools) and some are platform-specific,
so a full freeze would be neither minimal nor portable to the Linux CI. This pins
the top-level requirements deterministically; transitive resolution is left to
pip. If you later adopt ``pip-compile``/``uv``, replace this with their lock.

Usage:
    python scripts/gen_requirements_lock.py
"""

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REQUIREMENTS = REPO / "requirements.txt"
LOCK = REPO / "requirements.lock"


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def _installed() -> dict:
    """name(normalised) -> version, from `pip freeze`."""
    out = subprocess.run(
        [__import__("sys").executable, "-m", "pip", "freeze"],
        capture_output=True, text=True, check=True,
    ).stdout
    versions = {}
    for line in out.splitlines():
        line = line.strip()
        if "==" not in line or "@" in line:
            continue
        name, ver = line.split("==", 1)
        versions[_norm(name)] = ver
    return versions


def _requirement_parts(raw: str) -> tuple[str, str]:
    """Return (distribution name, extras suffix) from a requirement line."""
    spec = raw.split("#", 1)[0].strip()
    match = re.match(r"^([A-Za-z0-9_.-]+)(\[[^\]]+\])?", spec)
    if not match:
        return "", ""
    return match.group(1), match.group(2) or ""


def main() -> None:
    installed = _installed()
    lines = [
        "# Pinned direct runtime dependencies - generated from the validated env.",
        "# Regenerate: python scripts/gen_requirements_lock.py",
        "# CI and Docker install this file; optional DSS/GRIB extras are not included.",
        "",
    ]
    missing = []
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        name, extras = _requirement_parts(raw)
        if not name:
            continue
        version = installed.get(_norm(name))
        if version:
            # Preserve extras (e.g. uvicorn[standard]) - dropping them would
            # silently remove websockets/uvloop from the shipped image.
            lines.append(f"{name}{extras}=={version}")
        else:
            # Heavy/optional or not present in the dev env: do NOT put an
            # unpinned spec in the lock. An unpinned optional can silently
            # downgrade or conflict with the pinned core (for example,
            # pydsstools currently requires numpy<2 while the core pins
            # numpy 2.x). Keep optional packages in requirements.txt/docs.
            missing.append(name)

    if missing:
        lines.extend([
            "",
            "# Optional extras not installed in this environment:",
            "#   " + ", ".join(missing),
            "# They are intentionally omitted from the tested lock.",
        ])

    LOCK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {LOCK.name} ({len(lines)} lines)")
    if missing:
        print("WARNING - not installed locally, omitted from lock: " + ", ".join(missing))


if __name__ == "__main__":
    main()
