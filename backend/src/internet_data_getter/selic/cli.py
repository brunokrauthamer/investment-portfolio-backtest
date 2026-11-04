"""Selic status reporting and offline restore command."""
from datetime import datetime, timezone

from .storage import LockError, ManifestError, RestoreError, SelicFileStore


def print_report(report):
    print(f"Selic acquisition {'complete' if report.complete else 'incomplete'}")
    print(f"Status: {report.status}")
    print(f"Observations: {report.observations}")
    if report.first_date and report.last_date:
        print(f"Coverage: {report.first_date} through {report.last_date}")
    if report.sha256:
        print(f"SHA-256: {report.sha256}")
    for error in report.errors:
        print(f"Error: {error}")


def register_commands(subcommands):
    parser = subcommands.add_parser(
        "restore-selic", help="restore a verified Selic backup without contacting BCB"
    )
    parser.add_argument("--backup", required=True, help="manifest-listed Selic backup path")
    parser.set_defaults(command=restore)


def restore(args):
    store = SelicFileStore(args.data_dir)
    try:
        result = store.restore(args.backup, datetime.now(timezone.utc))
    except (LockError, ManifestError, RestoreError, OSError, ValueError) as exc:
        print(f"Selic restore failed: {exc}")
        return 1
    print(f"Selic restore complete: {result['status']} {result['path']}")
    return 0
