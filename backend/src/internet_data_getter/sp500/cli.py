"""S&P 500 command-line reporting, acquisition and offline recovery."""
from __future__ import annotations

from datetime import datetime, timezone

from . import acquire_sp500
from .storage import RestoreError, Sp500FileStore


def print_report(report) -> None:
    print(f"S&P 500 acquisition {'complete' if report.complete else 'incomplete'}")
    print(f"Status: {report.status}")
    print(f"Observations: {report.observations}")
    if report.first_date and report.last_date:
        print(f"Coverage: {report.first_date} through {report.last_date}")
    if report.added or report.updated:
        print(f"Added: {report.added}; updated: {report.updated}")
    if report.sha256:
        print(f"SHA-256: {report.sha256}")
    for window in report.requested_windows:
        if window.get("error"):
            print(
                f"Window failed: {window['start']} through {window['end']}: "
                f"{window['error']}"
            )
            continue
        print(f"Requested: {window['start']} through {window['end']}")
        if window.get("source_url"):
            print(f"Source URL: {window['source_url']}")
    for error in report.errors:
        print(f"Error: {error}")


def register_commands(subcommands) -> None:
    fetch = subcommands.add_parser(
        "fetch-sp500", help="fetch S&P 500 history using editable inclusive dates"
    )
    fetch.add_argument("--start-date", help="first date to request (YYYY-MM-DD; default 2011-01-03)")
    fetch.add_argument("--end-date", help="last date to request (YYYY-MM-DD; default today)")
    fetch.set_defaults(command=run_fetch)

    restore = subcommands.add_parser(
        "restore-sp500", help="restore a manifest-listed S&P 500 backup offline"
    )
    restore.add_argument("--backup", required=True, help="manifest-listed CSV or manifest backup path")
    restore.set_defaults(command=run_restore)


def run_fetch(args) -> int:
    report = acquire_sp500(args.data_dir, args.start_date, args.end_date)
    print_report(report)
    return 0 if report.complete else 1


def run_restore(args) -> int:
    store = Sp500FileStore(args.data_dir)
    try:
        result = store.restore(args.backup, datetime.now(timezone.utc))
    except (RestoreError, OSError, ValueError) as exc:
        print(f"S&P 500 restore failed: {exc}")
        return 1
    print(f"S&P 500 restore complete: {result['status']} {result['path']}")
    return 0
