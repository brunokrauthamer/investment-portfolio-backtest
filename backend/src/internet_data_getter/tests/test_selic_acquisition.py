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
    _set_date_filter,
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


def fake_selenium_values_page(metadata, rows, table_text):
    class Cell:
        def __init__(self, text):
            self.text = text

    class Row:
        def __init__(self, cells):
            self.cells = cells

        def find_elements(self, by, selector):
            if by != "css selector" or selector != "th, td":
                raise AssertionError((by, selector))
            return [Cell(text) for text in self.cells]

    class Table:
        id = "values-table"

        def __init__(self):
            self.text = table_text

        def is_displayed(self):
            return True

        def find_elements(self, by, selector):
            if by != "css selector" or selector != "tr":
                raise AssertionError((by, selector))
            return [Row(cells) for cells in rows]

    class Page:
        def find_element(self, by, selector):
            if by == "id" and selector == "seriesSelecionadas":
                return Cell(metadata)
            if by == "id" and selector == "valoresSeries":
                return Table()
            raise AssertionError((by, selector))

        def find_elements(self, by, selector):
            if by == "css selector" and selector == "#valoresSeries tr":
                return self.find_element("id", "valoresSeries").find_elements("css selector", "tr")
            raise AssertionError((by, selector))

    return Page()


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

    def test_browser_client_uses_selenium_for_complete_source_pages(self):
        import json

        class FakeElement:
            def __init__(self, driver, kind, text="", cells=()):
                self.driver = driver
                self.kind = kind
                self.text = text
                self.cells = cells
                self.id = f"{kind}-{driver.page.index}"

            def clear(self):
                self.driver.page.fills[self.kind] = ""

            def send_keys(self, value):
                if self.kind not in {"dataInicio", "dataFim"}:
                    self.driver.page.fills[self.kind] = value
                    return
                page = self.driver.page
                if "/" in value:
                    page.fills[self.kind] = "01//0/1/20" if self.kind == "dataInicio" else "04//0/1/20"
                    return
                digits = "".join(character for character in value if character.isdigit())
                formatted = f"{digits[:2]}/{digits[2:4]}/{digits[4:8]}"
                if page.corrupt_date_fields:
                    formatted = formatted[:-1]
                page.fills[self.kind] = formatted

            def get_attribute(self, name):
                if name != "value" or self.kind not in {"dataInicio", "dataFim"}:
                    raise AssertionError((self.kind, name))
                return self.driver.page.fills.get(self.kind, "")

            def is_displayed(self):
                return True

            def click(self):
                page = self.driver.page
                if self.kind == "refresh":
                    if not page.form_waited:
                        raise AssertionError("refresh clicked before the chart iframe form")
                    expected_dates = {"dataInicio": "01/01/2011", "dataFim": "04/01/2011"}
                    if page.fills != expected_dates:
                        raise AssertionError("refresh clicked with malformed date fields")
                    page.refreshed = True
                    self.driver.add_post("atualizarGraficoEstatico")
                elif self.kind == "values":
                    if not page.refreshed or not page.refresh_response_seen:
                        raise AssertionError("values opened before a successful chart refresh")
                    page.values_open = True
                elif self.kind == "next":
                    if not page.values_open:
                        raise AssertionError("pagination started before opening the values")
                    page.index += 1
                    self.driver.add_post("getPagina")
                else:
                    raise AssertionError(self.kind)

            def find_elements(self, by, value):
                if self.kind == "table" and by == "css selector" and value == "tr":
                    return [FakeElement(self.driver, "row", cells=row) for row in self.driver.page.rows_by_page[self.driver.page.index]]
                if self.kind == "row" and by == "css selector" and value == "th, td":
                    return [FakeElement(self.driver, "cell", text=cell) for cell in self.cells]
                raise AssertionError((self.kind, by, value))

        class FakePage:
            def __init__(self):
                self.index = 0
                self.fills = {}
                self.corrupt_date_fields = False
                self.form_waited = False
                self.refreshed = False
                self.refresh_response_seen = False
                self.values_open = False
                self.reported_count = 2
                self.rows_by_page = [
                    (("Date", "11 % p.d."), ("03/01/2011", "0,123456")),
                    (("04/01/2011", "0,123400"),),
                ]
                self.metadata = (
                    "11 - Interest rate - Selic % p.d.\n"
                    "Period 01/01/2011 to 04/01/2011\nLinear"
                )

        class SwitchTo:
            def __init__(self, driver):
                self.driver = driver

            def frame(self, _element):
                self.driver.in_frame = True
                if not self.driver.page.form_waited:
                    self.driver.page.form_waited = True

            def default_content(self):
                self.driver.in_frame = False

        class FakeDriver:
            def __init__(self):
                self.page = FakePage()
                self.switch_to = SwitchTo(self)
                self.in_frame = False
                self.logs = []
                self.quit_called = False
                self.url = None
                self.cdp_commands = []
                self.response_status = 200

            def set_page_load_timeout(self, timeout):
                if timeout <= 0:
                    raise AssertionError(timeout)

            def execute_cdp_cmd(self, command, params):
                self.cdp_commands.append((command, params))

            def get(self, url):
                self.url = url

            def find_element(self, by, value):
                page = self.page
                if by == "id" and value == "seriesSelecionadas":
                    return FakeElement(self, "metadata", text=page.metadata)
                if by == "id" and value in {"dataInicio", "dataFim"}:
                    return FakeElement(self, value)
                if by == "id" and value == "frmGraficoAlt":
                    return FakeElement(self, "frame")
                if by == "id" and value == "valoresSeries":
                    table_text = (
                        f"Found registers by series: {page.reported_count} "
                        "List of values Date DD/MM/YYYY 11 % p.d."
                    )
                    return FakeElement(self, "table", text=table_text)
                if by == "css selector" and "Refresh chart" in value:
                    return FakeElement(self, "refresh")
                if by == "css selector" and "View values from chart" in value:
                    return FakeElement(self, "values")
                if self.in_frame and by == "tag name" and value == "form":
                    return FakeElement(self, "form")
                if self.in_frame and by == "tag name" and value == "img":
                    return FakeElement(self, "chart-image")
                raise AssertionError((by, value, self.in_frame))

            def find_elements(self, by, value):
                if by == "link text" and value == "Next":
                    if self.page.index < len(self.page.rows_by_page) - 1:
                        return [FakeElement(self, "next"), FakeElement(self, "next")]
                    return []
                if by == "css selector" and value == "#valoresSeries tr":
                    return self.find_element("id", "valoresSeries").find_elements("css selector", "tr")
                raise AssertionError((by, value))

            def execute_script(self, script, *_args):
                if script == "return arguments[0].complete && arguments[0].naturalWidth > 0":
                    return self.in_frame
                if script == "return document.readyState":
                    return "complete"
                raise AssertionError(script)

            def add_post(self, method):
                request_id = f"request-{method}"
                url = f"https://www3.bcb.gov.br/sgspub/consultarvalores.do?method={method}"
                request = {"message": {"method": "Network.requestWillBeSent", "params": {
                    "requestId": request_id, "request": {"method": "POST", "url": url}
                }}}
                response = {"message": {"method": "Network.responseReceived", "params": {
                    "requestId": request_id, "response": {"status": self.response_status}
                }}}
                self.logs.extend(({"message": json.dumps(request)}, {"message": json.dumps(response)}))
                if method == "atualizarGraficoEstatico":
                    self.page.refresh_response_seen = True

            def get_log(self, name):
                if name != "performance":
                    raise AssertionError(name)
                logs, self.logs = self.logs, []
                return logs

            def quit(self):
                self.quit_called = True

        class DriverFactory:
            def __init__(self):
                self.driver = FakeDriver()
                self.options = None

            def __call__(self, options):
                self.options = options
                return self.driver

        factory = DriverFactory()
        result = SgsSelicClient(driver_factory=factory, pacing_seconds=0).fetch()
        self.assertEqual(factory.driver.url.split("?")[0], "https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do")
        self.assertEqual(factory.driver.page.fills, {"dataInicio": "01/01/2011", "dataFim": "04/01/2011"})
        self.assertIn("--headless=new", factory.options.arguments)
        self.assertEqual(
            factory.options.experimental_options.get("prefs", {}).get("intl.accept_languages"),
            "en-US,en",
        )
        self.assertEqual(factory.options.capabilities["goog:loggingPrefs"], {"performance": "ALL"})
        self.assertIn(("Network.enable", {}), factory.driver.cdp_commands)
        self.assertTrue(factory.driver.quit_called)
        self.assertEqual(result.reported_count, 2)
        self.assertEqual(result.observations, (
            Observation(date(2011, 1, 3), "0.123456"),
            Observation(date(2011, 1, 4), "0.123400"),
        ))

        malformed_factory = DriverFactory()
        malformed_factory.driver.page.corrupt_date_fields = True
        with self.assertRaisesRegex(SourceError, "BCB date filter dataInicio"):
            SgsSelicClient(driver_factory=malformed_factory, pacing_seconds=0).fetch()
        self.assertFalse(malformed_factory.driver.page.refreshed)
        self.assertTrue(malformed_factory.driver.quit_called)

        failed_factory = DriverFactory()
        failed_factory.driver.response_status = 500
        with self.assertRaisesRegex(SourceError, "returned HTTP 500"):
            SgsSelicClient(driver_factory=failed_factory, pacing_seconds=0).fetch()
        self.assertTrue(failed_factory.driver.quit_called)

        nonfinal_factory = DriverFactory()
        nonfinal_factory.driver.page.reported_count = 1
        with self.assertRaisesRegex(SourceError, "pagination continues after reported count"):
            SgsSelicClient(driver_factory=nonfinal_factory, pacing_seconds=0).fetch()

        repeated_factory = DriverFactory()
        repeated_factory.driver.page.rows_by_page = [
            (("Date", "11 % p.d."), ("03/01/2011", "0,123456")),
            (("03/01/2011", "0,123456"),),
        ]
        with self.assertRaisesRegex(SourceError, "repeated a values page"):
            SgsSelicClient(driver_factory=repeated_factory, pacing_seconds=0).fetch()

        missing_factory = DriverFactory()
        missing_factory.driver.page.rows_by_page = [
            (("Date", "11 % p.d."), ("03/01/2011", "0,123456")),
        ]
        with self.assertRaisesRegex(SourceError, "ended pagination before all observations"):
            SgsSelicClient(driver_factory=missing_factory, pacing_seconds=0).fetch()
    def test_fetch_forces_english_chrome_locale(self):
        captured = {}

        def stop_after_options(options):
            captured["options"] = options
            raise RuntimeError("stop after capturing Chrome options")

        with self.assertRaisesRegex(SourceError, "stop after capturing Chrome options"):
            SgsSelicClient(driver_factory=stop_after_options).fetch()

        self.assertEqual(
            captured["options"].experimental_options.get("prefs", {}).get("intl.accept_languages"),
            "en-US,en",
        )

    def test_masked_date_filter_types_digits_and_rejects_wrong_dom_value(self):
        class DateField:
            def __init__(self, corrupt=False):
                self.value = ""
                self.keys = []
                self.corrupt = corrupt

            def clear(self):
                self.value = ""

            def send_keys(self, keys):
                self.keys.append(keys)
                if not keys.isdigit():
                    self.value = "01//0/1/20"
                    return
                self.value = f"{keys[:2]}/{keys[2:4]}/{keys[4:8]}"
                if self.corrupt:
                    self.value = self.value[:-1]

            def get_attribute(self, name):
                if name != "value":
                    raise AssertionError(name)
                return self.value

        class Driver:
            def __init__(self, field):
                self.field = field

            def find_element(self, by, selector):
                if by != "id" or selector != "dataInicio":
                    raise AssertionError((by, selector))
                return self.field

        field = DateField()
        _set_date_filter(Driver(field), "dataInicio", "01/01/2011")
        self.assertEqual(field.keys, ["01012011"])
        self.assertEqual(field.value, "01/01/2011")

        malformed_field = DateField(corrupt=True)
        with self.assertRaisesRegex(SourceError, "expected '01/01/2011'"):
            _set_date_filter(Driver(malformed_field), "dataInicio", "01/01/2011")
        self.assertEqual(malformed_field.keys, ["01012011"])

    def test_values_page_checks_exact_series_code_in_metadata_and_header(self):
        cases = (
            ("111 - Interest rate - Selic % p.d.\nPeriod 01/01/2011 to 11/02/2011\nLinear", "111", "series 11 Selic"),
            ("11 - Interest rate - Selic % p.d.\nPeriod 01/01/2011 to 11/02/2011\nLinear", "111", "column header"),
        )
        for metadata, header_code, message in cases:
            page = fake_selenium_values_page(
                metadata,
                (("Date DD/MM/YYYY", f"{header_code} % p.d."), ("04/01/2011", "0,123400")),
                "Found registers by series: 1; List of values % p.d.",
            )
            with self.subTest(metadata=metadata.splitlines()[0], header_code=header_code):
                with self.assertRaisesRegex(SourceError, message):
                    _verify_values_page(page, "11/02/2011")

        exact_metadata = (
            "Search parameters\nSelected series\n\n11 - Interest rate - Selic\n\n"
            "Period\n\n01/01/2011 to 11/02/2011\tLinear"
        )
        page = fake_selenium_values_page(
            exact_metadata,
            (("Date DD/MM/YYYY", "11 % p.d."), ("04/01/2011", "0,123400")),
            "Found registers by series: 1; List of values % p.d.",
        )
        observations, count = _verify_values_page(page, "11/02/2011")
        self.assertEqual(count, 1)
        self.assertEqual(observations[0].rate, "0.123400")

    def test_values_page_rejects_changed_period_or_non_linear_function(self):
        for metadata, expected in (
            ("11 - Interest rate - Selic % p.d.\nPeriod 01/01/2011 to 05/01/2011\nLinear", "period differs"),
            ("11 - Interest rate - Selic % p.d.\nPeriod 01/01/2011 to 04/01/2011\nLogarithmic", "Linear"),
        ):
            page = fake_selenium_values_page(
                metadata,
                (("Date", "11 % p.d."), ("03/01/2011", "0,123456")),
                "Found registers by series: 1; List of values % p.d.",
            )
            with self.subTest(expected=expected), self.assertRaisesRegex(SourceError, expected):
                _verify_values_page(page, "04/01/2011")
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
