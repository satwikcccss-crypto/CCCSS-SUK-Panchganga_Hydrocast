# windows-v1.4.1 — Stable Repository & Documentation Consolidation

**Release date:** 2026-11-15  
**Target branch:** `windows-server-production`  
**Baseline:** `windows-v1.4.0`  
**Release type:** Stable patch — no hydrology or telemetry algorithm changes

---

## Highlights

- Consolidated the legacy documentation set into **27 maintained engineering manuals**.
- Preserved 18 legacy documents and 2 source modules that were not present in `main`.
- Removed 57 superseded Markdown files and 26 unused legacy `src/` modules after verifying they remain available in `main`.
- Added community health files, issue templates, accessibility guidance, and repository agent instructions.
- Added a public API documentation page and audit/visual verification suites.
- Added operator and GitHub-sync tooling while keeping credentials environment-driven.
- Redacted personal contact details and legacy credential examples from tracked documentation and source comments.

## Documentation

- Added a documentation index with validated internal navigation.
- Retained legacy non-Markdown diagrams and assets so existing architecture links remain valid.
- Corrected frontend README version/tag alignment.
- Added `docs/releases/windows-v1.4.1.md` and updated the release index.

## Repository Hygiene

- Ignored generated caches, screenshots, coverage artifacts, and local raw telemetry exports.
- Stopped committing generated runtime snapshots; runtime JSON files remain local/generated.
- Kept `graphify-out/` on disk but out of Git.
- Removed superseded source modules with no remaining imports.

## Community & Accessibility

- Added issue templates for bugs, feature requests, telemetry incidents, hydrology recalibration, and security incidents.
- Added pull request and accessibility guidance.
- Replaced personal email contacts with GitHub Security Advisory and issue-based contact paths.

## Verification

| Gate | Command / Check | Result |
|:---|:---|:---:|
| Backend tests | `py -m pytest tests/ -q --no-header` | **325 passed, 3 skipped** |
| Lint | `py -m ruff check backend tests scripts` | **Clean** |
| Public frontend build | `npm run build` in `frontend-public` | **Passed** |
| Admin frontend build | `npm run build` in `frontend-admin` | **Passed** |
| Documentation links | Local Markdown link scan | **0 missing** |
| Credential/contact scan | Tracked-file scan before tagging | **No live credentials or personal contacts found** |

## Upgrade Notes

- Restart the API, admin API, and both frontend services after deployment.
- No database migration is required for this patch release.
- Deployment should set `ACME_EMAIL` in the environment for Caddy ACME registration.
- The v1.4.0 IoT sensor corrections and telemetry integrity fixes remain included.

## Full Changelog

[`windows-v1.4.0...windows-v1.4.1`](https://github.com/satwikccss-crypto/CCCSS-SUK-Panchganga_Hydrocast/compare/windows-v1.4.0...windows-v1.4.1)
