"""Read-only validation of the acquired project Selic CSV and manifest."""
from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[4]
CSV_PATH = ROOT / "data/selic/source/selic_sgs_11.csv"
MANIFEST_PATH = ROOT / "data/selic/manifest.json"
EXPECTED_SAMPLES = {
    "2011-01-03": "0.040239",
    "2018-09-28": "0.024620",
    "2026-11-03": "0.050788",
}


def main() -> None:
    content = CSV_PATH.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    with CSV_PATH.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        headers = reader.fieldnames

    dates = [row["date"] for row in rows]
    parsed_dates = [date.fromisoformat(value) for value in dates]
    rates = [row["rate_percent_per_day"] for row in rows]
    samples = {
        sample_date: next(
            row["rate_percent_per_day"]
            for row in rows
            if row["date"] == sample_date
        )
        for sample_date in EXPECTED_SAMPLES
    }
    current = manifest["current"]
    checks = {
        "header": headers == ["date", "rate_percent_per_day"],
        "utf8": content.decode("utf-8") is not None,
        "unique_increasing_dates": parsed_dates == sorted(set(parsed_dates)),
        "canonical_dates_and_decimal_rates": all(
            parsed.isoformat() == raw_date for parsed, raw_date in zip(parsed_dates, dates)
        )
        and all(re.fullmatch(r"\d+(?:\.\d+)?", value) for value in rates),
        "rows_match_both_manifest_counts": len(rows)
        == current["observation_count"]
        == current["reported_count"],
        "date_coverage_matches_manifest": dates[0] == current["first_date"]
        and dates[-1] == current["last_date"]
        and dates[-1] == current["requested_end"],
        "requested_start_is_2011": current["requested_start"] == "2011-01-01",
        "hash_matches_manifest": digest == current["sha256"],
        "observed_source_samples_match": samples == EXPECTED_SAMPLES,
        "series_and_unit": manifest["series_id"] == 11
        and manifest["unit"] == "% p.d.",
        "license_provenance": manifest["license_listed_by_bcb"]
        == "Open Data Commons Open Database License (ODbL)",
    }
    output = {
        "csv_path": str(CSV_PATH.relative_to(ROOT)),
        "csv_bytes": len(content),
        "sha256": digest,
        "rows": len(rows),
        "first_date": dates[0],
        "last_date": dates[-1],
        "manifest_retrieved_at": current["retrieved_at"],
        "source_samples": samples,
        "checks": checks,
        "all_passed": all(checks.values()),
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if not output["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
