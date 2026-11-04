"""Independent, offline reproductions for initial-cycle round-3 findings."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from backend.src.internet_data_getter.sp500 import storage
from backend.src.internet_data_getter.sp500.source import (
    Observation,
    SourceError,
    YahooFinanceClient,
    build_history_url,
    parse_history_page,
)
from backend.src.internet_data_getter.sp500.storage import RestoreError, Sp500FileStore
from backend.src.internet_data_getter.tests.test_sp500_acquisition import HISTORY_HTML, _Response, page_result


START = date(2011, 1, 3)
END = date(2011, 1, 4)
NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


def reproduce_shifted_close() -> None:
    malformed = HISTORY_HTML.replace("<td>1,271.87</td>", "")
    parsed = parse_history_page(malformed, START, END)
    jan3 = next(item for item in parsed.observations if item.date == START)
    print(f"SP500-R3-01 reproduced: missing Close accepted, adjusted_close={jan3.adjusted_close!r}")


def reproduce_duplicate_blank_bound() -> None:
    requested = build_history_url(START, END)
    ambiguous = requested + "&period1="
    client = YahooFinanceClient(
        opener=lambda *_args, **_kwargs: _Response(HISTORY_HTML, ambiguous)
    )
    parsed = client.fetch(START, END)
    print(f"SP500-R3-03 reproduced: duplicate blank period1 accepted ({len(parsed.observations)} rows)")


def reproduce_conflicting_equity_identity() -> None:
    conflicting = HISTORY_HTML.replace(
        "<title>S&amp;P 500 (^GSPC) Historical Data</title>",
        "<title>Apple Inc. (AAPL) Historical Data</title>",
    )
    parsed = parse_history_page(conflicting, START, END)
    print(f"SP500-R3-04 reproduced: conflicting AAPL title accepted ({len(parsed.observations)} rows)")


def reproduce_lost_restore_reference() -> None:
    with tempfile.TemporaryDirectory() as temp:
        store = Sp500FileStore(Path(temp) / "data")
        first = ((START, "1271.87"),)
        first_page = page_result(START, END, list(first))
        store.save((Observation(*first[0]),), (first_page,), NOW)
        old_atomic_write = storage._atomic_write

        def interrupt_manifest(path, content):
            if path == store.manifest_path:
                raise OSError("simulated interruption after CSV replacement")
            old_atomic_write(path, content)

        updated = ((START, "1271.88"), (END, "1270.20"))
        updated_page = page_result(START, END, list(updated))
        with patch.object(storage, "_atomic_write", side_effect=interrupt_manifest):
            try:
                store.save(
                    tuple(Observation(*item) for item in updated),
                    (updated_page,),
                    datetime(2026, 11, 5, tzinfo=timezone.utc),
                )
            except OSError:
                pass
            else:
                raise AssertionError("the simulated manifest interruption did not occur")

        pending = json.loads(store.pending_path.read_text(encoding="utf-8"))
        backup = pending["backup"]
        pending["new_manifest"]["current"]["previous_versions"] = []
        proposed = store._manifest_bytes(pending["new_manifest"])
        pending["new_manifest_sha256"] = storage.sha256(proposed)
        store.pending_path.write_text(json.dumps(pending, indent=2), encoding="utf-8")

        store.load()
        try:
            store.restore(backup["csv_path"], datetime(2026, 11, 6, tzinfo=timezone.utc))
        except RestoreError as exc:
            print(f"SP500-R3-02 reproduced: recovery dropped restore reference: {exc}")
        else:
            raise AssertionError("the missing restore reference unexpectedly remained usable")


if __name__ == "__main__":
    for reproduce in (
        reproduce_shifted_close,
        reproduce_duplicate_blank_bound,
        reproduce_conflicting_equity_identity,
        reproduce_lost_restore_reference,
    ):
        try:
            reproduce()
        except (SourceError, RestoreError) as exc:
            print(f"Unexpected rejection in reproduction: {type(exc).__name__}: {exc}")
