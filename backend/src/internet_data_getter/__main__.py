"""Command-line coordination for registered data getters."""
from __future__ import annotations

import argparse
from pathlib import Path

from . import _GETTERS, acquire, available_getters


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Acquire historical data from registered sources and restore verified backups."
    )
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[3] / "data",
                        help="destination data directory (default: repository data/)")
    parser.add_argument("--getter", choices=available_getters(), help="run only the named getter (default: all)")
    subcommands = parser.add_subparsers(dest="operation")
    for getter in _GETTERS.values():
        getter.cli.register_commands(subcommands)
    args = parser.parse_args(argv)
    if args.operation:
        return args.command(args)

    names = (args.getter,) if args.getter else available_getters()
    complete = True
    for name in names:
        try:
            report = acquire(name, args.data_dir)
            _GETTERS[name].cli.print_report(report)
            complete = report.complete and complete
        except Exception as exc:
            print(f"{name} acquisition incomplete: {exc}")
            complete = False
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
