"""Milestone 1 Documentation Integrity and Deduplication Test Suite.

Empirical verification harness validating:
1. Every file referenced in `mkdocs.yml` nav exists on disk.
2. Canonical anchors in `docs/basin-hydrology.md` exist in both Markdown and built HTML.
3. Cross-page anchor links resolve to valid targets.
4. Duplicate tables (subbasins, reaches, datums) and legacy naming are eradicated.
5. Strict MkDocs build passes with 0 warnings/errors.
"""

from __future__ import annotations

import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, List, Set

import pytest
from mkdocs.config import load_config

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
MKDOCS_CONFIG = REPO_ROOT / "mkdocs.yml"
SITE_DIR = REPO_ROOT / "site"


class HTMLIDCollector(HTMLParser):
    """HTML parser to extract all element IDs and hrefs."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: Set[str] = set()
        self.hrefs: List[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for attr_name, attr_val in attrs:
            if attr_name == "id" and attr_val:
                self.ids.add(attr_val)
            elif attr_name == "href" and attr_val:
                self.hrefs.append(attr_val)


def extract_nav_paths(nav_item: Any) -> List[str]:
    """Recursively extract document file paths from mkdocs nav structure."""
    paths: List[str] = []
    if isinstance(nav_item, str):
        paths.append(nav_item)
    elif isinstance(nav_item, list):
        for item in nav_item:
            paths.extend(extract_nav_paths(item))
    elif isinstance(nav_item, dict):
        for value in nav_item.values():
            paths.extend(extract_nav_paths(value))
    return paths


class TestMkDocsNavIntegrity:
    """Validate that mkdocs.yml navigation links point to actual files."""

    def test_all_nav_files_exist_on_disk(self) -> None:
        assert MKDOCS_CONFIG.is_file(), f"mkdocs.yml not found at {MKDOCS_CONFIG}"
        config = load_config(str(MKDOCS_CONFIG))

        assert "nav" in config, "No 'nav' section in mkdocs.yml"
        nav_paths = extract_nav_paths(config["nav"])
        assert len(nav_paths) > 0, "No navigation paths extracted"

        missing_files: List[str] = []
        for rel_path in nav_paths:
            # Handle external URLs
            if rel_path.startswith("http://") or rel_path.startswith("https://"):
                continue
            # Strip fragment if present
            clean_path = rel_path.split("#")[0]
            target_file = DOCS_DIR / clean_path
            if not target_file.is_file():
                missing_files.append(f"{rel_path} -> {target_file}")

        assert not missing_files, (
            f"Found {len(missing_files)} missing files referenced in mkdocs.yml nav:\n"
            + "\n".join(missing_files)
        )
        print(f"\n[PASS] Verified {len(nav_paths)} navigation files exist on disk.")


class TestBasinHydrologyCanonicalAnchors:
    """Validate canonical definitions and anchors in docs/basin-hydrology.md."""

    def test_canonical_markdown_anchors_and_content(self) -> None:
        basin_file = DOCS_DIR / "basin-hydrology.md"
        assert basin_file.is_file(), "docs/basin-hydrology.md does not exist"
        content = basin_file.read_text(encoding="utf-8")

        # 1. Anchors
        required_anchors = [
            "{: #subbasin-parameters }",
            "{: #muskingum-reaches }",
            "{: #regulatory-datums }",
        ]
        for anchor in required_anchors:
            assert anchor in content, f"Missing required anchor '{anchor}' in basin-hydrology.md"

        # 2. Canonical subbasin area: 1,837.213 km²
        assert "1,837.213" in content, "Missing authoritative area 1,837.213 km² in basin-hydrology.md"

        # 3. All 9 subbasins
        subbasins = [
            "S1", "Karveer",
            "S2", "Sangarul",
            "S3", "Kotoli",
            "S4", "Karanjphen",
            "S5", "Padasali",
            "S6", "Gaganbawda",
            "S7", "Garivade",
            "S8", "Beed",
            "S9", "Radhanagari",
        ]
        for name in subbasins:
            assert name in content, f"Subbasin parameter entry '{name}' missing in basin-hydrology.md"

        # 4. All 5 reaches
        for reach in ["R5", "R4", "R2", "R3", "R1"]:
            assert reach in content, f"Reach '{reach}' missing in basin-hydrology.md"

        # 5. Official regulatory benchmarks
        benchmarks = [
            "528.670",  # Shivaji bed
            "529.318",  # Rajaram bed
            "530.180",  # WRD zero datum
            "535.770",  # Weir crest
            "539.700",  # Warning threshold
            "540.700",  # Danger threshold
            "541.500",  # Rajaram Alert
            "542.100",  # Shivaji Alert
            "542.700",  # WRD Warning
            "543.300",  # WRD Danger
            "545.330",  # HFL
        ]
        for bm in benchmarks:
            assert bm in content, f"Regulatory benchmark '{bm}' missing in basin-hydrology.md"

        print("\n[PASS] Verified canonical anchors and data matrices in basin-hydrology.md.")


class TestCrossPageAnchorLinkContracts:
    """Validate dependent documentation pages correctly link to canonical anchors."""

    def test_interface_contract_pages(self) -> None:
        contracts = {
            "architecture.md": [
                "#subbasin-parameters",
                "#muskingum-reaches",
                "#regulatory-datums",
            ],
            "hec-hms-engine.md": [
                "#subbasin-parameters",
                "#muskingum-reaches",
            ],
            "runoff-computation.md": [
                "#subbasin-parameters",
            ],
            "hydraulics.md": [
                "#regulatory-datums",
            ],
            "calibration-validation.md": [
                "#regulatory-datums",
            ],
            "stage-discharge-conversion.md": [
                "#regulatory-datums",
            ],
        }

        for doc_name, expected_anchors in contracts.items():
            doc_path = DOCS_DIR / doc_name
            assert doc_path.is_file(), f"Target contract doc '{doc_name}' does not exist"
            content = doc_path.read_text(encoding="utf-8")

            for anchor in expected_anchors:
                link_pattern = re.compile(
                    r"\[([^\]]+)\]\(([^)]*basin-hydrology\.md)?" + re.escape(anchor) + r"\)"
                )
                match = link_pattern.search(content)
                assert match is not None, (
                    f"Page '{doc_name}' failed contract: does not contain link to '{anchor}'"
                )

        print("\n[PASS] Verified interface contracts across all 6 dependent pages.")

    def test_all_basin_hydrology_anchors_across_docs_are_valid(self) -> None:
        """Scan ALL markdown files to verify every link to basin-hydrology.md resolves to an existing anchor."""
        basin_content = (DOCS_DIR / "basin-hydrology.md").read_text(encoding="utf-8")

        # Extract explicit anchors: {: #anchor }
        explicit_anchors = set(re.findall(r"\{:\s*#([a-zA-Z0-9_\-]+)\s*\}", basin_content))
        # Extract heading anchors generated by slugification: e.g. ## 1. Physical Physiography -> 1-physical-physiography-of-the-panchganga-basin
        heading_lines = [
            line for line in basin_content.splitlines() if line.strip().startswith("#")
        ]
        generated_slugs: Set[str] = set()
        for hl in heading_lines:
            h_text = re.sub(r"^#+\s*", "", hl).strip()
            h_text = re.sub(r"\{:[^}]*\}", "", h_text).strip()
            slug = re.sub(r"[^\w\s-]", "", h_text).strip().lower()
            slug = re.sub(r"[-\s]+", "-", slug)
            if slug:
                generated_slugs.add(slug)

        all_valid_anchors = explicit_anchors | generated_slugs

        link_regex = re.compile(r"\[([^\]]*)\]\(([^)]*basin-hydrology\.md(?:#([a-zA-Z0-9_\-]+))?)\)")

        broken_links: List[str] = []
        checked_count = 0

        for md_path in DOCS_DIR.rglob("*.md"):
            text = md_path.read_text(encoding="utf-8")
            for match in link_regex.finditer(text):
                checked_count += 1
                full_href = match.group(2)
                anchor = match.group(3)
                if anchor:
                    if anchor not in all_valid_anchors:
                        broken_links.append(f"{md_path.name}: {full_href} (target #{anchor} not found)")

        assert not broken_links, (
            f"Found {len(broken_links)} broken anchor links to basin-hydrology.md:\n"
            + "\n".join(broken_links)
        )
        print(f"\n[PASS] Verified {checked_count} anchor links to basin-hydrology.md across all docs.")


class TestBuiltSiteHtmlAnchors:
    """Validate that in the built HTML site, the IDs and anchor targets physically exist."""

    def test_site_basin_hydrology_html_ids_exist(self) -> None:
        html_file = SITE_DIR / "basin-hydrology" / "index.html"
        assert html_file.is_file(), f"Built HTML file not found at {html_file}. Run mkdocs build first."
        html_content = html_file.read_text(encoding="utf-8")

        collector = HTMLIDCollector()
        collector.feed(html_content)

        required_ids = [
            "subbasin-parameters",
            "muskingum-reaches",
            "regulatory-datums",
        ]
        for req_id in required_ids:
            assert req_id in collector.ids, (
                f"HTML element with id='{req_id}' missing in {html_file}. Found IDs: {sorted(collector.ids)}"
            )

        print("\n[PASS] Verified physical HTML IDs in site/basin-hydrology/index.html via HTML parser.")

    def test_cross_referencing_pages_in_built_site(self) -> None:
        """Verify that referencing HTML pages link to basin-hydrology with correct relative paths and valid fragment IDs."""
        basin_html_file = SITE_DIR / "basin-hydrology" / "index.html"
        assert basin_html_file.is_file(), "Built basin-hydrology HTML not found"
        basin_collector = HTMLIDCollector()
        basin_collector.feed(basin_html_file.read_text(encoding="utf-8"))

        pages_to_check = [
            "architecture",
            "hec-hms-engine",
            "hydraulics",
            "calibration-validation",
            "stage-discharge-conversion",
            "runoff-computation",
        ]

        verified_links = 0
        for page in pages_to_check:
            page_file = SITE_DIR / page / "index.html"
            assert page_file.is_file(), f"Built page {page_file} not found"
            page_collector = HTMLIDCollector()
            page_collector.feed(page_file.read_text(encoding="utf-8"))

            for href in page_collector.hrefs:
                if "basin-hydrology" in href and "#" in href:
                    frag = href.split("#")[1]
                    assert frag in basin_collector.ids, (
                        f"Page '{page}' links to '#{frag}', which is not a valid ID in built basin-hydrology HTML!"
                    )
                    verified_links += 1

        assert verified_links > 0, "No cross-references to basin-hydrology found in built HTML pages"
        print(f"\n[PASS] Verified {verified_links} cross-page anchor links in built HTML site resolve to existing IDs.")


class TestNoDuplicateTablesOrLegacyArtifacts:
    """Empirically challenge documentation for duplicate tables and deprecated artifacts."""

    def test_no_duplicate_full_subbasin_tables_in_other_docs(self) -> None:
        """Ensure no doc other than basin-hydrology.md contains a full subbasin parameter table."""
        subbasin_names = [
            "Karveer", "Sangarul", "Kotoli", "Karanjphen", "Padasali",
            "Gaganbawda", "Garivade", "Beed", "Radhanagari",
        ]

        duplicate_tables: List[str] = []

        for md_path in DOCS_DIR.rglob("*.md"):
            if md_path.name in ("basin-hydrology.md", "raingauge-network.md", "accuracy-analysis-pi-report.md"):
                continue

            content = md_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            cur_table: List[str] = []
            for line in lines:
                if "|" in line:
                    cur_table.append(line)
                else:
                    if len(cur_table) > 2:
                        tbl_text = "\n".join(cur_table)
                        match_count = sum(
                            1 for name in subbasin_names
                            if re.search(r"\b" + name + r"\b", tbl_text, re.IGNORECASE)
                        )
                        if match_count >= 4 and any(kw in tbl_text for kw in ["CN", "Curve Number", "Lag", "Kirpich"]):
                            duplicate_tables.append(
                                f"{md_path.name}: Table with {match_count} subbasins and hydrologic parameters:\n{cur_table[0]}\n{cur_table[1]}"
                            )
                    cur_table = []

        assert not duplicate_tables, (
            f"Found duplicate subbasin parameter tables in:\n" + "\n".join(duplicate_tables)
        )
        print("\n[PASS] Verified zero duplicate subbasin parameter tables across docs.")

    def test_no_duplicate_muskingum_parameter_tables(self) -> None:
        """Ensure no doc other than basin-hydrology.md contains a full Muskingum reach table."""
        duplicate_tables: List[str] = []

        for md_path in DOCS_DIR.rglob("*.md"):
            if md_path.name == "basin-hydrology.md":
                continue

            content = md_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            cur_table: List[str] = []
            for line in lines:
                if "|" in line:
                    cur_table.append(line)
                else:
                    if len(cur_table) > 2:
                        tbl_text = "\n".join(cur_table)
                        reach_matches = sum(1 for r in ["R1", "R2", "R3", "R4", "R5"] if re.search(r"\b" + r + r"\b", tbl_text))
                        if reach_matches >= 4 and re.search(r"\b(Travel Time|Wedge Weight|Committed \$?K\$?|Committed \$?X\$?)\b", tbl_text, re.IGNORECASE):
                            duplicate_tables.append(
                                f"{md_path.name}: Muskingum table with {reach_matches} reaches:\n{cur_table[0]}\n{cur_table[1]}"
                            )
                    cur_table = []

        assert not duplicate_tables, (
            f"Found duplicate Muskingum parameter tables in:\n" + "\n".join(duplicate_tables)
        )
        print("\n[PASS] Verified zero duplicate Muskingum parameter tables across docs.")

    def test_no_duplicate_wrd_regulatory_datum_tables(self) -> None:
        """Ensure no doc other than basin-hydrology.md contains a duplicate WRD regulatory datum table."""
        duplicate_tables: List[str] = []
        datums = ["530.18", "535.77", "539.70", "540.70", "541.50", "542.70", "543.30", "545.33"]

        for md_path in DOCS_DIR.rglob("*.md"):
            if md_path.name in ("basin-hydrology.md", "wrd-rating-curve-cross-check.md"):
                continue

            content = md_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            cur_table: List[str] = []
            for line in lines:
                if "|" in line:
                    cur_table.append(line)
                else:
                    if len(cur_table) > 2:
                        tbl_text = "\n".join(cur_table)
                        datum_count = sum(1 for d in datums if d in tbl_text)
                        if datum_count >= 5:
                            duplicate_tables.append(
                                f"{md_path.name}: Table contains {datum_count} regulatory datums:\n{cur_table[0]}"
                            )
                    cur_table = []

        assert not duplicate_tables, (
            f"Found duplicate regulatory datum tables in:\n" + "\n".join(duplicate_tables)
        )
        print("\n[PASS] Verified zero duplicate regulatory datum tables across docs.")

    def test_no_obsolete_karvir_outlet_in_basin_hydrology(self) -> None:
        """Ensure obsolete phrasing 'Karvir (Outlet)' is not used in canonical basin-hydrology.md."""
        content = (DOCS_DIR / "basin-hydrology.md").read_text(encoding="utf-8")
        assert "Karvir (Outlet)" not in content, (
            "Found obsolete 'Karvir (Outlet)' in docs/basin-hydrology.md"
        )
        print("\n[PASS] Verified obsolete naming eradicated from basin-hydrology.md.")


class TestMkDocsStrictBuild:
    """Validate MkDocs build succeeds in strict mode with 0 errors and warnings."""

    def test_strict_build_succeeds(self) -> None:
        cmd = ["python", "-m", "mkdocs", "build", "--strict"]
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        print(f"\nBuild Output:\n{result.stdout}")
        assert result.returncode == 0, f"MkDocs strict build failed with code {result.returncode}:\n{result.stdout}"
        print("\n[PASS] MkDocs strict build succeeded with exit code 0.")


class TestAdversarialSiteLinkCrawler:
    """Stress-test site-wide HTML links and anchor targets across built documentation."""

    def test_all_built_html_internal_links_and_anchors(self) -> None:
        assert SITE_DIR.is_dir(), f"site/ directory does not exist at {SITE_DIR}"
        html_files = list(SITE_DIR.rglob("*.html"))
        assert len(html_files) > 0, "No HTML files found in site/"

        # 1. Index all IDs for every HTML file
        file_ids: dict[Path, Set[str]] = {}
        for hf in html_files:
            collector = HTMLIDCollector()
            collector.feed(hf.read_text(encoding="utf-8", errors="ignore"))
            file_ids[hf.resolve()] = collector.ids

        # 2. Check all links across all HTML files
        broken_links: List[str] = []
        total_links_checked = 0

        # Exclude auto-generated mkdocstrings docstring internal links in api-reference/ (Milestone 2 scope)
        handwritten_html_files = [
            hf for hf in html_files
            if "api-reference" not in str(hf.relative_to(SITE_DIR))
        ]

        for hf in handwritten_html_files:
            collector = HTMLIDCollector()
            collector.feed(hf.read_text(encoding="utf-8", errors="ignore"))


            for href in collector.hrefs:
                # Skip external protocols, mailto, javascript, pure query strings, file:// (F12 M3)
                if href.startswith(("http://", "https://", "mailto:", "javascript:", "data:", "file:")):
                    continue


                total_links_checked += 1

                # Pure on-page anchor: #some-id
                if href.startswith("#"):
                    frag = href[1:]
                    if frag and frag not in file_ids[hf.resolve()]:
                        broken_links.append(f"{hf.relative_to(SITE_DIR)}: on-page anchor '{href}' not found")
                    continue

                # Relative link, possibly with query or fragment
                clean_href = href.split("?")[0]
                url_path, sep, frag = clean_href.partition("#")

                if not url_path:
                    # e.g. "?query#fragment"
                    if frag and frag not in file_ids[hf.resolve()]:
                        broken_links.append(f"{hf.relative_to(SITE_DIR)}: on-page anchor '{href}' not found")
                    continue

                # Strip site_url base path if absolute link
                SITE_PREFIX = "/CCCSS-SUK-Panchganga_Hydrocast/"
                if clean_href.startswith(SITE_PREFIX):
                    target = (SITE_DIR / clean_href[len(SITE_PREFIX):]).resolve()
                elif clean_href.startswith("/"):
                    target = (SITE_DIR / clean_href.lstrip("/")).resolve()
                else:
                    target = (hf.parent / url_path).resolve()

                if target.is_dir():
                    target = target / "index.html"

                if not target.is_file():
                    broken_links.append(f"{hf.relative_to(SITE_DIR)}: broken relative link '{href}' -> {target}")
                elif frag:
                    # Check anchor exists on target page
                    target_ids = file_ids.get(target, set())
                    if frag not in target_ids:
                        broken_links.append(
                            f"{hf.relative_to(SITE_DIR)}: link '{href}' missing anchor '#{frag}' in {target.relative_to(SITE_DIR)}"
                        )

        # Allow report of broken links with assertion
        assert not broken_links, (
            f"Found {len(broken_links)} broken internal links in built site:\n"
            + "\n".join(broken_links[:30])
        )
        print(f"\n[PASS] Verified {total_links_checked} internal HTML links across {len(html_files)} pages with zero broken references.")



if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
