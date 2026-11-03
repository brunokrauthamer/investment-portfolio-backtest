"""Command-line entry point for explicit IFIX downloads and offline restore."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from backend.src.acquisition.ifix_source import B3IfixClient, DownloadError, available_years
from backend.src.application.ifix_acquisition import AcquisitionReport, IfixAcquisition
from backend.src.storage.ifix import FileStore, LockError, ManifestError, SaveResult


def _print_report(report: AcquisitionReport) -> None:
    print(f"IFIX acquisition {'complete' if report.complete else 'incomplete'}")
    print(f"Saved: {report.saved or 'none'}")
    print(f"Updated: {report.updated or 'none'}")
    print(f"Unchanged: {report.unchanged or 'none'}")
    if report.errors:
        print("Errors:")
        for period, message in report.errors.items():
            print(f"  {period}: {message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download or restore B3 IFIX daily-evolution source CSV files.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "data",
        help="destination data directory (default: repository data/)",
    )
    subcommands = parser.add_subparsers(dest="operation")
    restore_parser = subcommands.add_parser("restore", help="restore a verified backup without contacting B3")
    restore_parser.add_argument("--year", required=True, type=int, help="IFIX annual period to restore")
    restore_parser.add_argument(
        "--backup", required=True, help="manifest-relative backup path for that year"
    )
    args = parser.parse_args(argv)
    store = FileStore(args.data_dir)

    if args.operation == "restore":
        try:
            with store.lock():
                result = store.restore(args.year, args.backup, datetime.now(timezone.utc))
        except (LockError, ManifestError, OSError, ValueError) as exc:
            print(f"IFIX restore failed: {exc}")
            return 1
        print(f"Restored IFIX {result.year} from {args.backup}")
        if result.backup:
            print(f"Displaced active file backed up to {result.backup}")
        return 0

    try:
        report = IfixAcquisition(B3IfixClient(), store).run()
    except (LockError, OSError) as exc:
        print(f"IFIX acquisition incomplete: {exc}")
        return 1
    _print_report(report)
    return 0 if report.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
