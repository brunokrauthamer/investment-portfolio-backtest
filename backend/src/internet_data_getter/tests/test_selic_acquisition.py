"""Selic acquisition behavior, using controlled observations only."""
from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
import hashlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from backend.src.internet_data_getter import available_getters
from backend.src.internet_data_getter.selic.source import (
    Observation,
    SgsSelicClient,
    SourceError,
    SourceResult,
    parse_observation_rows,
    parse_rate,
    _verify_values_page,
    validate_observations,
)
from backend.src.internet_data_getter.selic.storage import (
    LockError,
    ManifestError,
    SelicFileStore,
    StoreError,
    csv_bytes,
)
from backend.src.internet_data_getter.selic.service import SelicAcquisition


def sample_result(values=("0.123456", "0.123400")):
    return SourceResult(
        (
            Observation(date(2011, 1, 3), values[0].replace(",", ".")),
            Observation(date(2011, 1, 4), values[1].replace(",", ".")),
        ),
        date(2011, 1, 4),
        2,
    )


class SelicRegistryTests(unittest.TestCase):
    def test_selic_is_registered_as_an_explicit_getter(self):
        self.assertIn("selic", available_getters())

    def test_parser_preserves_display_precision_and_ignores_headers(self):
        rows = parse_observation_rows(
            (("Date", "11 % p.d."), ("03/01/2011", "0,123456"), ("Source", "BCB-Demab"))
        )
        self.assertEqual(rows, (Observation(date(2011, 1, 3), "0.123456"),))
        self.assertEqual(parse_rate("0,040000"), "0.040000")

    def test_parser_rejects_invalid_percentages_and_rows(self):
        for value in ("0,04x", "1.234,5", "-0,1", ""):
            with self.subTest(value=value), self.assertRaises(SourceError):
                parse_rate(value)
        with self.assertRaisesRegex(SourceError, "malformed observation"):
            parse_observation_rows((("03/01/2011", "0,04", "extra"),))

    def test_validation_rejects_wrong_count_order_and_latest_date(self):
        values = sample_result().observations
        for observations, latest, count, message in (
            (values, date(2011, 1, 4), 3, "reported 3"),
            ((values[1], values[0]), date(2011, 1, 3), 2, "out of date order"),
            (values, date(2011, 1, 5), 2, "source latest date"),
            ((Observation(date(2012, 1, 3), "0.04"),), date(2012, 1, 3), 1, "in 2011"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(SourceError, message):
                validate_observations(observations, latest, count)

    def test_parser_rejects_a_malformed_date_with_numeric_rate(self):
        rows = (
            ("Date DD/MM/YYYY", "11 % p.d."),
            ("02/02/2011", "9,991"),
            ("03-02-2011", "9,992"),
            ("04/02/2011", "9,993"),
            ("Source", "BCB-Demab"),
        )
        with self.assertRaisesRegex(SourceError, "malformed observation date"):
            parse_observation_rows(rows)

    def test_store_saves_exact_csv_and_unchanged_rerun_creates_no_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            expected = b"date,rate_percent_per_day\n2011-01-03,0.123456\n2011-01-04,0.123400\n"
            with store.lock():
                result = store.save_locked(sample_result(), datetime(2026, 11, 3, tzinfo=timezone.utc))
            self.assertEqual(store.active_path.read_bytes(), expected)
            self.assertEqual(result["status"], "saved")
            before = store.active_path.stat().st_mtime_ns
            with store.lock():
                result = store.save_locked(sample_result(), datetime(2026, 11, 4, tzinfo=timezone.utc))
            self.assertEqual(result["status"], "unchanged")
            self.assertEqual(store.active_path.stat().st_mtime_ns, before)
            self.assertFalse(store.backup_root.exists())
            manifest = json.loads(store.manifest_path.read_text("utf-8"))
            self.assertEqual(manifest["current"]["sha256"], hashlib.sha256(expected).hexdigest())
            self.assertEqual(manifest["current"]["observation_count"], 2)

    def test_unchanged_save_rejects_corrupt_provenance_and_preserves_files(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            with store.lock():
                store.save_locked(sample_result(), datetime(2026, 11, 3, tzinfo=timezone.utc))
            csv_before = store.active_path.read_bytes()
            manifest = json.loads(store.manifest_path.read_text("utf-8"))
            manifest.pop("unit")
            manifest["current"]["retrieved_at"] = None
            manifest["current"]["observation_count"] = 99
            store.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            manifest_before = store.manifest_path.read_bytes()

            with store.lock():
                with self.assertRaisesRegex(ManifestError, "unit|retrieval|count"):
                    store.save_locked(sample_result(), datetime(2026, 11, 4, tzinfo=timezone.utc))

            self.assertEqual(store.active_path.read_bytes(), csv_before)
            self.assertEqual(store.manifest_path.read_bytes(), manifest_before)

    def test_unchanged_save_rejects_counts_that_disagree_with_the_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            with store.lock():
                store.save_locked(sample_result(), datetime(2026, 11, 3, tzinfo=timezone.utc))
            manifest = json.loads(store.manifest_path.read_text("utf-8"))
            manifest["current"]["reported_count"] = 99
            manifest["current"]["observation_count"] = 99
            store.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with store.lock():
                with self.assertRaisesRegex(ManifestError, "CSV observation counts"):
                    store.save_locked(sample_result(), datetime(2026, 11, 4, tzinfo=timezone.utc))

    def test_changed_csv_is_backed_up_and_manifested(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            with store.lock():
                store.save_locked(sample_result(), datetime(2026, 11, 3, tzinfo=timezone.utc))
            old = store.active_path.read_bytes()
            changed = SourceResult(
                (Observation(date(2011, 1, 3), "0.050001"), Observation(date(2011, 1, 4), "0.060002")),
                date(2011, 1, 4), 2,
            )
            with store.lock():
                result = store.save_locked(changed, datetime(2026, 11, 4, tzinfo=timezone.utc))
            manifest = json.loads(store.manifest_path.read_text("utf-8"))
            references = manifest["current"]["previous_versions"]
            self.assertEqual(result["status"], "updated")
            self.assertNotEqual(store.active_path.read_bytes(), old)
            self.assertEqual(len(references), 1)
            self.assertNotIn("record", references[0])
            backup = store.data_root / references[0]["csv_path"]
            self.assertEqual(backup.read_bytes(), old)
            self.assertEqual(hashlib.sha256(backup.read_bytes()).hexdigest(), references[0]["csv_sha256"])

    def test_failed_atomic_active_write_leaves_previous_csv_and_pending_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            with store.lock():
                store.save_locked(sample_result(), datetime(2026, 11, 3, tzinfo=timezone.utc))
            old = store.active_path.read_bytes()
            changed = SourceResult(
                (Observation(date(2011, 1, 3), "0.050001"), Observation(date(2011, 1, 4), "0.060002")),
                date(2011, 1, 4), 2,
            )
            from backend.src.internet_data_getter.selic import storage

            atomic_write = storage._atomic_write

            def fail_active(path, content):
                if path == store.active_path:
                    raise OSError("simulated active replace failure")
                return atomic_write(path, content)

            with patch("backend.src.internet_data_getter.selic.storage._atomic_write", side_effect=fail_active):
                with store.lock():
                    with self.assertRaisesRegex(OSError, "simulated active"):
                        store.save_locked(changed, datetime(2026, 11, 4, tzinfo=timezone.utc))
            self.assertEqual(store.active_path.read_bytes(), old)
            self.assertTrue(store.pending_path.exists())
            with store.lock():
                store.recover()
            self.assertFalse(store.pending_path.exists())
            manifest = json.loads(store.manifest_path.read_text("utf-8"))
            self.assertEqual(len(manifest["current"]["previous_versions"]), 1)

    def test_store_lock_rejects_overlapping_operation(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            with store.lock():
                with self.assertRaises(LockError):
                    with store.lock():
                        pass

    def test_restore_uses_only_a_hash_verified_manifest_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            with store.lock():
                store.save_locked(sample_result(), datetime(2026, 11, 3, tzinfo=timezone.utc))
            old = store.active_path.read_bytes()
            changed = SourceResult(
                (Observation(date(2011, 1, 3), "0.050001"), Observation(date(2011, 1, 4), "0.060002")),
                date(2011, 1, 4), 2,
            )
            with store.lock():
                store.save_locked(changed, datetime(2026, 11, 4, tzinfo=timezone.utc))
            manifest = json.loads(store.manifest_path.read_text("utf-8"))
            backup_ref = manifest["current"]["previous_versions"][0]["csv_path"]
            result = store.restore(backup_ref, datetime(2026, 11, 5, tzinfo=timezone.utc))
            self.assertEqual(result["status"], "updated")
            self.assertEqual(store.active_path.read_bytes(), old)

    def test_restore_preserves_source_retrieval_time_and_records_local_restore_time(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            retrieved_at = datetime(2026, 2, 1, tzinfo=timezone.utc)
            with store.lock():
                store.save_locked(sample_result(), retrieved_at)
            original_record = json.loads(store.manifest_path.read_text("utf-8"))["current"]
            changed = SourceResult(
                (Observation(date(2011, 1, 3), "0.654321"), Observation(date(2011, 1, 4), "0.654300")),
                date(2011, 1, 4), 2,
            )
            with store.lock():
                store.save_locked(changed, datetime(2026, 2, 10, tzinfo=timezone.utc))
            current = json.loads(store.manifest_path.read_text("utf-8"))["current"]
            backup_ref = current["previous_versions"][0]["csv_path"]

            store.restore(backup_ref, datetime(2026, 2, 11, tzinfo=timezone.utc))

            restored = json.loads(store.manifest_path.read_text("utf-8"))["current"]
            self.assertEqual(restored["retrieved_at"], original_record["retrieved_at"])
            self.assertEqual(restored["restored_at"], "2026-02-11T00:00:00Z")

    def test_recovery_preserves_unknown_manifest_and_pending_record(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            with store.lock():
                store.save_locked(sample_result(), datetime(2026, 11, 3, tzinfo=timezone.utc))
            changed = SourceResult(
                (Observation(date(2011, 1, 3), "0.456789"), Observation(date(2011, 1, 4), "0.456700")),
                date(2011, 1, 4), 2,
            )
            from backend.src.internet_data_getter.selic import storage

            atomic_write = storage._atomic_write

            def fail_manifest(path, content):
                if path == store.manifest_path:
                    raise OSError("simulated manifest replace failure")
                return atomic_write(path, content)

            with patch("backend.src.internet_data_getter.selic.storage._atomic_write", side_effect=fail_manifest):
                with store.lock():
                    with self.assertRaisesRegex(OSError, "simulated manifest"):
                        store.save_locked(changed, datetime(2026, 11, 4, tzinfo=timezone.utc))
            store.manifest_path.write_bytes(b"unrecognized external manifest bytes")
            pending_before = store.pending_path.read_bytes()
            manifest_before = store.manifest_path.read_bytes()

            with store.lock():
                with self.assertRaisesRegex(StoreError, "manifest matches neither known"):
                    store.recover()

            self.assertEqual(store.manifest_path.read_bytes(), manifest_before)
            self.assertEqual(store.pending_path.read_bytes(), pending_before)

    def test_recovery_recognizes_an_already_written_rollback_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            with store.lock():
                store.save_locked(sample_result(), datetime(2026, 11, 3, tzinfo=timezone.utc))
            old_csv = store.active_path.read_bytes()
            changed = SourceResult(
                (Observation(date(2011, 1, 3), "0.765432"), Observation(date(2011, 1, 4), "0.765400")),
                date(2011, 1, 4), 2,
            )
            from backend.src.internet_data_getter.selic import storage

            atomic_write = storage._atomic_write

            def fail_active(path, content):
                if path == store.active_path:
                    raise OSError("simulated active replace failure")
                return atomic_write(path, content)

            with patch("backend.src.internet_data_getter.selic.storage._atomic_write", side_effect=fail_active):
                with store.lock():
                    with self.assertRaisesRegex(OSError, "simulated active"):
                        store.save_locked(changed, datetime(2026, 11, 4, tzinfo=timezone.utc))

            def crash_after_manifest_replace(path, content):
                result = atomic_write(path, content)
                if path == store.manifest_path:
                    raise OSError("simulated recovery interruption")
                return result

            with patch(
                "backend.src.internet_data_getter.selic.storage._atomic_write",
                side_effect=crash_after_manifest_replace,
            ):
                with store.lock():
                    with self.assertRaisesRegex(OSError, "recovery interruption"):
                        store.recover()
            self.assertTrue(store.pending_path.exists())
            rollback_manifest = store.manifest_path.read_bytes()

            with store.lock():
                store.recover()

            self.assertFalse(store.pending_path.exists())
            self.assertEqual(store.active_path.read_bytes(), old_csv)
            self.assertEqual(store.manifest_path.read_bytes(), rollback_manifest)

    def test_repeated_updates_keep_current_manifest_history_flat(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SelicFileStore(Path(temp) / "data")
            for revision in range(10):
                rate = f"{revision + 1:01d}.123456"
                result = SourceResult(
                    (Observation(date(2011, 1, 3), rate), Observation(date(2011, 1, 4), rate)),
                    date(2011, 1, 4), 2,
                )
                with store.lock():
                    store.save_locked(result, datetime(2026, 11, revision + 1, tzinfo=timezone.utc))

            manifest_size = store.manifest_path.stat().st_size
            self.assertLess(manifest_size, 20_000, f"current manifest grew to {manifest_size} bytes")

    def test_browser_client_sets_source_range_refreshes_opens_values_and_pages(self):
        class FormLocator:
            def __init__(self, page):
                self.page = page

            @property
            def first(self):
                return self

            def wait_for(self, state, timeout):
                if state != "attached" or timeout <= 0:
                    raise AssertionError((state, timeout))
                self.page.form_waited = True

        class ResponseWaiter:
            def __init__(self, page, predicate):
                self.page, self.predicate = page, predicate

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                method_name = "getPagina" if self.page.paging else "atualizarGraficoEstatico"
                response = type("Response", (), {
                    "request": type("Request", (), {"method": "POST"})(),
                    "url": f"https://www3.bcb.gov.br/sgspub/consultarvalores.do?method={method_name}",
                    "status": 200,
                })()
                if not self.predicate(response):
                    raise AssertionError("expected BCB POST response was not observed")
                self.page.refresh_response_seen = True
                self.value = response

        class NavigationWaiter:
            def __init__(self, page):
                self.page = page

            def __enter__(self):
                self.page.waiting_navigation = True
                return self

            def __exit__(self, *_args):
                self.page.waiting_navigation = False
                if not self.page.paging:
                    raise AssertionError("BCB page transition was not observed")

        class ImageLocator:
            def __init__(self, page):
                self.page = page

            def wait_for(self, state, timeout):
                if state != "visible" or timeout <= 0:
                    raise AssertionError((state, timeout))
                self.page.waited_for_refresh = True

            def evaluate(self, expression):
                if expression != "image => image.complete && image.naturalWidth > 0":
                    raise AssertionError(expression)
                return self.page.waited_for_refresh

        class FrameLocator:
            def __init__(self, page):
                self.page = page

            def locator(self, selector):
                if selector == "form":
                    return FormLocator(self.page)
                if selector != "img":
                    raise AssertionError(selector)
                return ImageLocator(self.page)

        class CellLocator:
            def __init__(self, cells):
                self.cells = cells

            def all_inner_texts(self):
                return self.cells

        class RowLocator:
            def __init__(self, cells):
                self.cells = cells

            def locator(self, _selector):
                return CellLocator(self.cells)

        class NextLink:
            def __init__(self, page):
                self.page = page
                self.first_match = False

            def count(self):
                return 2 * int(self.page.index < len(self.page.rows_by_page) - 1)

            @property
            def first(self):
                self.first_match = True
                return self

            def click(self):
                if not self.first_match:
                    raise AssertionError("Next is ambiguous at the top and bottom of the table")
                if not self.page.waiting_navigation:
                    raise AssertionError("Next clicked without waiting for the page transition")
                self.page.paging = True
                self.page.index += 1

        class Locator:
            def __init__(self, page, selector):
                self.page, self.selector = page, selector

            def inner_text(self):
                if self.selector == "#seriesSelecionadas":
                    if self.page.values_open:
                        return "11 - Interest rate - Selic % p.d.\nPeriod 01/01/2011 to 04/01/2011\nLinear"
                    return (
                        "Found series\nCode\n\t\nFull name\n\t\nUnit\n\t\nPer.\n\t\n"
                        "Start\n\t\nLast value\n\t\nY Axis\n\n"
                        "11\tInterest rate - Selic\t% p.d.\tD\t04/06/1986\t04/01/2011\t\n"
                        "Primary\nSecondary"
                    )
                if self.selector == "#valoresSeries":
                    return (
                        f"Found registers by series: {self.page.reported_count} List of values (Number format: European) "
                        "Date DD/MM/YYYY 11 % p.d."
                    )
                raise AssertionError(self.selector)

            def fill(self, value):
                self.page.fills[self.selector] = value

            def click(self):
                if self.selector == "input.botao[value='Refresh chart']":
                    if not self.page.form_waited:
                        raise AssertionError("refresh clicked before static chart iframe form attached")
                    self.page.refreshed = True
                elif self.selector == "input.botao[value='View values from chart']":
                    if not self.page.refreshed:
                        raise AssertionError("values opened before refresh")
                    if not self.page.waited_for_refresh:
                        raise AssertionError("values opened before the refreshed chart finished loading")
                    if not self.page.refresh_response_seen:
                        raise AssertionError("values opened before the refresh POST completed")
                    self.page.values_open = True
                else:
                    raise AssertionError(self.selector)

            def all(self):
                if self.selector == "#valoresSeries tr":
                    return [RowLocator(cells) for cells in self.page.rows_by_page[self.page.index]]
                raise AssertionError(self.selector)

        class FakePage:
            def __init__(self):
                self.index = 0
                self.fills = {}
                self.refreshed = False
                self.form_waited = False
                self.refresh_response_seen = False
                self.waiting_navigation = False
                self.paging = False
                self.waited_for_refresh = False
                self.values_open = False
                self.reported_count = 2
                self.rows_by_page = [
                    (("Date", "11 % p.d."), ("03/01/2011", "0,123456")),
                    (("04/01/2011", "0,123400"),),
                ]

            def set_default_timeout(self, _value):
                pass

            def goto(self, url, wait_until):
                self.url, self.wait_until = url, wait_until

            def locator(self, selector):
                return Locator(self, selector)

            def get_by_role(self, role, name, exact):
                if role != "link" or name != "Next" or not exact:
                    raise AssertionError((role, name, exact))
                return NextLink(self)

            def frame_locator(self, selector):
                if selector != "#frmGraficoAlt":
                    raise AssertionError(selector)
                return FrameLocator(self)

            def wait_for_load_state(self, state, timeout):
                if state != "networkidle" or timeout <= 0:
                    raise AssertionError((state, timeout))
                self.waited_for_refresh = True

            def expect_response(self, predicate, timeout):
                if timeout <= 0:
                    raise AssertionError(timeout)
                return ResponseWaiter(self, predicate)

            def expect_navigation(self, wait_until, timeout):
                if wait_until != "domcontentloaded" or timeout <= 0:
                    raise AssertionError((wait_until, timeout))
                return NavigationWaiter(self)

        class Browser:
            def __init__(self):
                self.page = FakePage()

            def new_page(self):
                return self.page

            def close(self):
                pass

        class Runtime:
            def __init__(self):
                self.chromium = self
                self.browser = Browser()

            def launch(self, headless):
                if not headless:
                    raise AssertionError("expected headless browser")
                return self.browser

        class Context:
            def __init__(self):
                self.runtime = Runtime()

            def __enter__(self):
                return self.runtime

            def __exit__(self, *_args):
                pass

        context = Context()
        result = SgsSelicClient(playwright_factory=lambda: context, pacing_seconds=0).fetch()
        page = context.runtime.browser.page
        self.assertEqual(page.url.startswith("https://www3.bcb.gov.br/sgspub/"), True)
        self.assertEqual(page.fills, {"#dataInicio": "01/01/2011", "#dataFim": "04/01/2011"})
        self.assertTrue(page.refreshed)
        self.assertTrue(page.values_open)
        self.assertEqual(result.reported_count, 2)
        self.assertEqual(result.observations[0], Observation(date(2011, 1, 3), "0.123456"))

        nonfinal_context = Context()
        nonfinal_page = nonfinal_context.runtime.browser.page
        nonfinal_page.reported_count = 1
        nonfinal_page.rows_by_page = [
            (("Date", "11 % p.d."), ("04/01/2011", "0,123400")),
            (("05/01/2011", "0,654321"),),
        ]
        with self.assertRaisesRegex(SourceError, "pagination continues after reported count"):
            SgsSelicClient(playwright_factory=lambda: nonfinal_context, pacing_seconds=0).fetch()

        repeated_context = Context()
        repeated_page = repeated_context.runtime.browser.page
        repeated_page.reported_count = 2
        repeated_page.rows_by_page = [
            (("Date", "11 % p.d."), ("03/01/2011", "0,123456")),
            (("03/01/2011", "0,123456"),),
        ]
        with self.assertRaisesRegex(SourceError, "repeated a values page"):
            SgsSelicClient(playwright_factory=lambda: repeated_context, pacing_seconds=0).fetch()

        missing_context = Context()
        missing_page = missing_context.runtime.browser.page
        missing_page.reported_count = 2
        missing_page.rows_by_page = [
            (("Date", "11 % p.d."), ("03/01/2011", "0,123456")),
        ]
        with self.assertRaisesRegex(SourceError, "ended pagination before all observations"):
            SgsSelicClient(playwright_factory=lambda: missing_context, pacing_seconds=0).fetch()

    def test_values_page_checks_exact_series_code_in_metadata_and_header(self):
        class Cells:
            def __init__(self, values):
                self.values = values

            def all_inner_texts(self):
                return self.values

        class Row:
            def __init__(self, values):
                self.values = values

            def locator(self, _selector):
                return Cells(self.values)

        class Locator:
            def __init__(self, text="", rows=()):
                self.text, self.rows = text, rows

            def inner_text(self):
                return self.text

            def all(self):
                return [Row(row) for row in self.rows]

        class Page:
            def __init__(self, metadata, header_code):
                self.metadata = metadata
                self.header_code = header_code

            def locator(self, selector):
                if selector == "#seriesSelecionadas":
                    return Locator(self.metadata)
                if selector == "#valoresSeries":
                    return Locator(
                        f"Found registers by series: 1 Date DD/MM/YYYY {self.header_code} % p.d."
                    )
                if selector == "#valoresSeries tr":
                    return Locator(rows=(("Date DD/MM/YYYY", f"{self.header_code} % p.d."),
                                         ("04/01/2011", "0,123400")))
                raise AssertionError(selector)

        cases = (
            ("111 - Interest rate - Selic % p.d.\nPeriod 01/01/2011 to 11/02/2011\nLinear", "111", "series 11 Selic"),
            ("11 - Interest rate - Selic % p.d.\nPeriod 01/01/2011 to 11/02/2011\nLinear", "111", "column header"),
        )
        for metadata, header_code, message in cases:
            with self.subTest(metadata=metadata.splitlines()[0], header_code=header_code):
                with self.assertRaisesRegex(SourceError, message):
                    _verify_values_page(Page(metadata, header_code), "11/02/2011")

        exact_metadata = (
            "Search parameters\nSelected series\n\n11 - Interest rate - Selic\n\n"
            "Period\n\n01/01/2011 to 11/02/2011\tLinear"
        )
        observations, count = _verify_values_page(Page(exact_metadata, "11"), "11/02/2011")
        self.assertEqual(count, 1)
        self.assertEqual(observations[0].rate, "0.123400")

    def test_values_page_rejects_changed_period_or_non_linear_function(self):
        class CellLocator:
            def __init__(self, cells):
                self.cells = cells

            def all_inner_texts(self):
                return self.cells

        class RowLocator:
            def __init__(self, cells):
                self.cells = cells

            def locator(self, _selector):
                return CellLocator(self.cells)

        class Locator:
            def __init__(self, text="", rows=()):
                self.text, self.rows = text, rows

            def inner_text(self):
                return self.text

            def all(self):
                return [RowLocator(row) for row in self.rows]

        class Page:
            def __init__(self, metadata):
                self.metadata = metadata

            def locator(self, selector):
                if selector == "#seriesSelecionadas":
                    return Locator(self.metadata)
                if selector == "#valoresSeries":
                    return Locator("Found registers by series: 1; % p.d.")
                if selector == "#valoresSeries tr":
                    return Locator(rows=(("Date", "11 % p.d."), ("03/01/2011", "0,123456")))
                return Locator("")

        for metadata, expected in (
            ("11 - Interest rate - Selic % p.d.\nPeriod 01/01/2011 to 05/01/2011\nLinear", "period differs"),
            ("11 - Interest rate - Selic % p.d.\nPeriod 01/01/2011 to 04/01/2011\nLogarithmic", "Linear"),
        ):
            with self.subTest(expected=expected), self.assertRaisesRegex(SourceError, expected):
                _verify_values_page(Page(metadata), "04/01/2011")

    def test_service_returns_incomplete_report_on_source_denial(self):
        class DeniedClient:
            def fetch(self):
                raise SourceError("BCB denied request")

        with tempfile.TemporaryDirectory() as temp:
            report = SelicAcquisition(DeniedClient(), SelicFileStore(Path(temp) / "data")).run()
            self.assertFalse(report.complete)
            self.assertEqual(report.errors, ["BCB denied request"])
            self.assertFalse((Path(temp) / "data/selic/source/selic_sgs_11.csv").exists())


if __name__ == "__main__":
    unittest.main()
