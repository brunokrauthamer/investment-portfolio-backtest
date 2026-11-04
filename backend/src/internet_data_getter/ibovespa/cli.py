"""IBOVESPA reporting and offline restore command."""
from datetime import datetime, timezone

from .storage import FileStore, LockError, ManifestError


def print_report(report):
    print(f"IBOVESPA acquisition {'complete' if report.complete else 'incomplete'}")
    print(f"Saved: {report.saved or 'none'}")
    print(f"Updated: {report.updated or 'none'}")
    print(f"Unchanged: {report.unchanged or 'none'}")
    if report.errors:
        print("Errors:")
        for period, message in report.errors.items():
            print(f"  {period}: {message}")


def register_commands(subcommands):
    parser = subcommands.add_parser("restore-ibovespa", help="restore a verified IBOVESPA backup without contacting B3")
    parser.add_argument("--year", required=True, type=int, help="IBOVESPA annual period to restore")
    parser.add_argument("--backup", required=True, help="manifest-relative backup path for that year")
    parser.set_defaults(command=restore)


def restore(args):
    store = FileStore(args.data_dir)
    try:
        with store.lock():
            result = store.restore(args.year, args.backup, datetime.now(timezone.utc))
    except (LockError, ManifestError, OSError, ValueError) as exc:
        print(f"IBOVESPA restore failed: {exc}")
        return 1
    print(f"Restored IBOVESPA {result.year} from {args.backup}")
    if result.backup:
        print(f"Displaced active file backed up to {result.backup}")
    return 0
