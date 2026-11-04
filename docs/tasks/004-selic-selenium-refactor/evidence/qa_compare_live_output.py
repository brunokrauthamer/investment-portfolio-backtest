"""Compare independent live BCB table samples to QA's temporary CLI CSV."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


task = Path(__file__).resolve().parent.parent
data = task / "qa-live-data"
source = json.loads((task / "evidence" / "qa-bcb-source-comparison.json").read_text())
manifest = json.loads((data / "selic" / "manifest.json").read_text())
csv_path = data / "selic" / "source" / "selic_sgs_11.csv"
rows = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
indices = {
    "first": 0,
    "middle": source["source_samples"]["middle_index"],
    "last": len(rows) - 1,
}
actual_samples = {name: rows[index] for name, index in indices.items()}
source_samples = {
    name: source["source_samples"][name]
    for name in ("first", "middle", "last")
}
checks = {
    "cli_csv_row_count_matches_live_source": len(rows) == source["reported_count"],
    "manifest_count_matches_csv_and_source": (
        manifest["current"]["observation_count"]
        == len(rows)
        == source["reported_count"]
    ),
    "manifest_reported_count_matches_source": (
        manifest["current"]["reported_count"] == source["reported_count"]
    ),
    "cli_range_matches_live_source": [
        rows[0]["date"],
        rows[-1]["date"],
    ]
    == source["source_date_range"],
    "manifest_sha256_matches_cli_csv": digest == manifest["current"]["sha256"],
    "first_middle_last_values_match_live_source": actual_samples == source_samples,
}
result = {
    "live_source_evidence": "evidence/qa-bcb-source-comparison.json",
    "cli_manifest": "qa-live-data/selic/manifest.json",
    "csv_sha256": digest,
    "csv_observation_count": len(rows),
    "csv_date_range": [rows[0]["date"], rows[-1]["date"]],
    "source_samples": source_samples,
    "cli_samples": actual_samples,
    "checks": checks,
    "passed": all(checks.values()),
}
print(json.dumps(result, indent=2))
if not result["passed"]:
    raise SystemExit(1)
