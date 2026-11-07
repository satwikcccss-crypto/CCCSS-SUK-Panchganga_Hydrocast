#!/usr/bin/env node
/**
 * npm audit gate for HydroCast.
 *
 * `npm audit` currently reports known Next.js 14 / PostCSS advisories that are
 * tracked by the Next 16 migration (P0 #6). This gate allows only the advisory
 * IDs listed in `audit-allowlist.json`; any *new* high or critical advisory
 * fails CI. Remove IDs from the allowlist as upgrades land.
 */

import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const allowlistPath = join(here, "..", "audit-allowlist.json");
const allowlist = new Set(
  JSON.parse(readFileSync(allowlistPath, "utf8")).advisories,
);

let raw;
try {
  raw = execSync("npm audit --omit=dev --json", {
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024,
  });
} catch (error) {
  // npm exits 1 when vulnerabilities exist; the JSON report is still on stdout.
  raw = error.stdout;
  if (!raw) {
    console.error("npm audit did not produce a JSON report.");
    console.error(error.message);
    process.exit(2);
  }
}

let report;
try {
  report = JSON.parse(raw);
} catch (error) {
  console.error("Could not parse npm audit JSON:", error.message);
  process.exit(2);
}

if (report.error || !report.metadata) {
  console.error(
    "npm audit did not return a valid report:",
    report.error || "metadata missing",
  );
  process.exit(2);
}

const blocked = [];
for (const [name, vuln] of Object.entries(report.vulnerabilities || {})) {
  if (!["high", "critical"].includes(vuln.severity)) continue;

  const advisories = (vuln.via || [])
    .filter((via) => typeof via === "object" && via.url)
    .map((via) => via.url.split("/").pop())
    .filter(Boolean);

  const unallowed = advisories.filter((id) => !allowlist.has(id));
  if (unallowed.length > 0 || advisories.length === 0) {
    blocked.push({
      name,
      severity: vuln.severity,
      unallowed: unallowed.length ? unallowed : ["no advisory id"],
    });
  }
}

if (blocked.length > 0) {
  console.error("Blocking npm advisories (not in audit-allowlist.json):");
  for (const item of blocked) {
    console.error(
      `- ${item.name} (${item.severity}): ${item.unallowed.join(", ")}`,
    );
  }
  process.exit(1);
}

const known = Object.values(report.vulnerabilities || {}).filter((vuln) =>
  ["high", "critical"].includes(vuln.severity),
).length;
console.log(
  `npm audit gate passed: ${known} known high/critical package(s) are allow-listed.`,
);
