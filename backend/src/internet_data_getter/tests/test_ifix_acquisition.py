import base64
import contextlib
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import urllib.error
import hashlib

from backend.src.internet_data_getter.ifix.b3_source import B3IfixClient, DownloadError, available_years
from backend.src.internet_data_getter.ifix.service import IfixAcquisition
from backend.src.internet_data_getter.ifix.storage import FileStore, LockError


def csv_bytes(year: int, marker: str = "TEST_FIXTURE_A") -> bytes:
    lines = [
        f"IFIX - {year}",
        "Dia;Jan;Fev;Mar;Abr;Mai;Jun;Jul;Ago;Set;Out;Nov;Dez",
    ]
    for day in range(1, 32):
        cells = [str(day)] + ([marker] + [""] * 11 if day == 1 else [""] * 12)
        lines.append(";".join(cells))
    lines.extend([";".join(["MÍNIMO", "TEST_METADATA"] + [""] * 11), ";".join(["MÁXIMO", "TEST_METADATA"] + [""] * 11)])
    return ("\r\n".join(lines) + "\r\n").encode("cp1252")


class FakeResponse:
    status = 200

    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


class IfixSourceTests(unittest.TestCase):
    def test_years_cover_2011_through_current_year(self):
        self.assertEqual(available_years(2026), list(range(2011, 2027)))
        self.assertEqual(available_years(2010), [])

    def test_client_decodes_the_original_annual_csv_bytes(self):
        expected = csv_bytes(2011)
        request_urls = []

        def opener(url, timeout):
            request_urls.append(url)
            self.assertGreater(timeout, 0)
            return FakeResponse(base64.b64encode(expected))

        client = B3IfixClient(opener=opener, sleeper=lambda _: None)
        self.assertEqual(client.download_year(2011), expected)
        self.assertEqual(len(request_urls), 1)
        encoded = request_urls[0].rsplit("/", 1)[1]
        self.assertEqual(
            json.loads(base64.b64decode(encoded)),
            {"index": "IFIX", "language": "pt-br", "year": "2011"},
        )

    def test_client_rejects_invalid_base64_and_wrong_year(self):
        with self.subTest("invalid base64"):
            client = B3IfixClient(
                opener=lambda *_args, **_kwargs: FakeResponse(b"<html>denied</html>"),
                sleeper=lambda _: None,
            )
            with self.assertRaises(DownloadError):
                client.download_year(2011)
        with self.subTest("wrong year"):
            client = B3IfixClient(
                opener=lambda *_args, **_kwargs: FakeResponse(base64.b64encode(csv_bytes(2012))),
                sleeper=lambda _: None,
            )
            with self.assertRaises(DownloadError):
                client.download_year(2011)

    def test_client_observes_pacing_and_reports_http_errors(self):
        delays = []
        client = B3IfixClient(
            opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                urllib.error.HTTPError("https://b3.invalid", 503, "busy", {}, None)
            ),
            sleeper=delays.append,
            pacing_seconds=0.25,
        )
        with self.assertRaisesRegex(DownloadError, "request failed"):
            client.download_year(2011)
        self.assertEqual(delays, [0.25])

    def test_client_rejects_truncated_annual_matrix(self):
        truncated = (
            b"IFIX - 2011\r\n"
            b"Dia;Jan;Fev;Mar;Abr;Mai;Jun;Jul;Ago;Set;Out;Nov;Dez\r\n"
            b"1;TEST_FIXTURE_TRUNCATED\r\n"
        )
        client = B3IfixClient(
            opener=lambda *_args, **_kwargs: FakeResponse(base64.b64encode(truncated)),
            sleeper=lambda _: None,
        )
        with self.assertRaises(DownloadError):
            client.download_year(2011)

    def test_client_accepts_partial_current_year_with_blank_future_months(self):
        content = csv_bytes(2026, "TEST_FIXTURE_PARTIAL_YEAR")
        client = B3IfixClient(
            opener=lambda *_args, **_kwargs: FakeResponse(base64.b64encode(content)),
            sleeper=lambda _: None,
        )
        self.assertEqual(client.download_year(2026), content)


class FileStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = FileStore(self.root / "data")

    def tearDown(self):
        self.temp.cleanup()

    def test_saves_original_bytes_and_manifest(self):
        data = csv_bytes(2011)
        record = self.store.save(2011, data, datetime(2026, 11, 3, tzinfo=timezone.utc))
        active = self.root / "data/ifix/source/IFIX_2011_Evolucao_Diaria.csv"
        manifest = json.loads((self.root / "data/ifix/manifest.json").read_text("utf-8"))
        self.assertEqual(active.read_bytes(), data)
        self.assertEqual(record.status, "saved")
        self.assertEqual(manifest["files"]["2011"]["sha256"], record.sha256)
        self.assertEqual(manifest["files"]["2011"]["source_filename"], "Evolucao_Diaria.csv")

    def test_unchanged_bytes_keep_mtime_and_create_no_backup(self):
        data = csv_bytes(2011)
        self.store.save(2011, data, datetime(2026, 11, 3, tzinfo=timezone.utc))
        active = self.root / "data/ifix/source/IFIX_2011_Evolucao_Diaria.csv"
        before = active.stat().st_mtime_ns
        result = self.store.save(2011, data, datetime(2026, 11, 4, tzinfo=timezone.utc))
        self.assertEqual(result.status, "unchanged")
        self.assertEqual(active.stat().st_mtime_ns, before)
        self.assertEqual(list((self.root / "data/backups/ifix").glob("**/*")) if (self.root / "data/backups/ifix").exists() else [], [])

    def test_changed_bytes_are_backed_up_before_atomic_replace(self):
        old = csv_bytes(2011, "TEST_FIXTURE_OLD")
        new = csv_bytes(2011, "TEST_FIXTURE_NEW")
        self.store.save(2011, old, datetime(2026, 11, 3, tzinfo=timezone.utc))
        result = self.store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
        active = self.root / "data/ifix/source/IFIX_2011_Evolucao_Diaria.csv"
        backups = list((self.root / "data/backups/ifix/2011").glob("*.csv"))
        self.assertEqual(result.status, "updated")
        self.assertEqual(active.read_bytes(), new)
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), old)
        manifest = json.loads((self.root / "data/ifix/manifest.json").read_text("utf-8"))
        self.assertEqual(
            manifest["files"]["2011"]["previous_versions"][0]["path"],
            backups[0].relative_to(self.root / "data").as_posix(),
        )

    def test_backup_failure_preserves_active_file(self):
        old = csv_bytes(2011)
        self.store.save(2011, old, datetime(2026, 11, 3, tzinfo=timezone.utc))
        with patch.object(self.store, "_write_backup", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.store.save(2011, csv_bytes(2011, "TEST_FIXTURE_NEW"), datetime.now(timezone.utc))
        self.assertEqual((self.root / "data/ifix/source/IFIX_2011_Evolucao_Diaria.csv").read_bytes(), old)

    def test_replace_failure_preserves_active_file_and_verified_backup(self):
        old = csv_bytes(2011)
        new = csv_bytes(2011, "TEST_FIXTURE_NEW")
        self.store.save(2011, old, datetime(2026, 11, 3, tzinfo=timezone.utc))
        active = self.root / "data/ifix/source/IFIX_2011_Evolucao_Diaria.csv"
        from backend.src.internet_data_getter.ifix import storage as storage_ifix

        atomic_write = storage_ifix._atomic_write

        def fail_active_write(path, content):
            if path == active:
                raise OSError("replace failed")
            atomic_write(path, content)

        with patch("backend.src.internet_data_getter.ifix.storage._atomic_write", side_effect=fail_active_write):
            with self.assertRaisesRegex(OSError, "replace failed"):
                self.store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
        backups = list((self.root / "data/backups/ifix/2011").glob("*.csv"))
        self.assertEqual(active.read_bytes(), old)
        self.assertEqual([path.read_bytes() for path in backups], [old])

    def test_invalid_manifest_prevents_active_file_changes(self):
        active = self.root / "data/ifix/source/IFIX_2011_Evolucao_Diaria.csv"
        active.parent.mkdir(parents=True)
        old = csv_bytes(2011)
        active.write_bytes(old)
        self.store.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.store.manifest_path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(OSError):
                self.store.save(2011, csv_bytes(2011, "TEST_FIXTURE_NEW"), datetime.now(timezone.utc))
        self.assertEqual(active.read_bytes(), old)

    def test_manifest_with_wrong_json_shape_fails_safely(self):
        self.store.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.store.manifest_path.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(OSError, "unsupported format"):
            self.store.save(2011, csv_bytes(2011), datetime.now(timezone.utc))

    def test_nested_manifest_record_is_rejected_before_active_replacement(self):
        active = self.root / "data/ifix/source/IFIX_2011_Evolucao_Diaria.csv"
        old = csv_bytes(2011, "TEST_FIXTURE_OLD")
        active.parent.mkdir(parents=True)
        active.write_bytes(old)
        self.store.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        for record in (None, {"previous_versions": "invalid"}):
            with self.subTest(record=record):
                self.store.manifest_path.write_text(
                    json.dumps({"schema_version": 1, "source": "https://source.invalid", "files": {"2011": record}}),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(OSError, "2011"):
                    self.store.save(2011, csv_bytes(2011, "TEST_FIXTURE_NEW"), datetime.now(timezone.utc))
                self.assertEqual(active.read_bytes(), old)

    def test_manifest_write_interruption_keeps_backup_reference_for_rerun(self):
        old = csv_bytes(2011, "TEST_FIXTURE_OLD")
        new = csv_bytes(2011, "TEST_FIXTURE_NEW")
        self.store.save(2011, old, datetime(2026, 11, 3, tzinfo=timezone.utc))
        from backend.src.internet_data_getter.ifix import storage as storage_ifix

        atomic_write = storage_ifix._atomic_write
        active = self.root / "data/ifix/source/IFIX_2011_Evolucao_Diaria.csv"

        def fail_after_active_replacement(path, content):
            if path == self.store.manifest_path and active.exists() and active.read_bytes() == new:
                raise OSError("manifest replace failed")
            atomic_write(path, content)

        with patch("backend.src.internet_data_getter.ifix.storage._atomic_write", side_effect=fail_after_active_replacement):
            with self.assertRaisesRegex(OSError, "manifest replace failed"):
                self.store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
        result = self.store.save(2011, new, datetime(2026, 11, 5, tzinfo=timezone.utc))
        manifest = json.loads(self.store.manifest_path.read_text("utf-8"))
        self.assertEqual(result.status, "unchanged")
        self.assertEqual(len(manifest["files"]["2011"]["previous_versions"]), 1)
        backup = self.root / "data" / manifest["files"]["2011"]["previous_versions"][0]["path"]
        self.assertEqual(hashlib.sha256(backup.read_bytes()).hexdigest(), manifest["files"]["2011"]["previous_versions"][0]["sha256"])

    def test_lock_rejects_an_overlapping_run(self):
        with self.store.lock():
            with self.assertRaises(LockError):
                with self.store.lock():
                    pass


class AcquisitionTests(unittest.TestCase):
    def test_partial_source_error_is_reported_and_successes_are_saved(self):
        class Client:
            def download_year(self, year):
                if year == 2012:
                    raise DownloadError("source unavailable")
                return csv_bytes(year)

        with tempfile.TemporaryDirectory() as temp:
            store = FileStore(Path(temp) / "data")
            result = IfixAcquisition(Client(), store, current_year=2013).run(
                now=datetime(2026, 11, 3, tzinfo=timezone.utc)
            )
            self.assertFalse(result.complete)
            self.assertEqual(result.errors, {2012: "source unavailable"})
            self.assertTrue((Path(temp) / "data/ifix/source/IFIX_2011_Evolucao_Diaria.csv").exists())
            self.assertTrue((Path(temp) / "data/ifix/source/IFIX_2013_Evolucao_Diaria.csv").exists())

    def test_no_available_years_is_incomplete(self):
        class UnusedClient:
            def download_year(self, year):
                raise AssertionError("no request should be made")

        with tempfile.TemporaryDirectory() as temp:
            result = IfixAcquisition(UnusedClient(), FileStore(Path(temp) / "data"), 2010).run()
        self.assertFalse(result.complete)
        self.assertIn("discovery", result.errors)

    def test_cli_reports_destination_errors_without_a_traceback(self):
        from backend.src.internet_data_getter import __main__ as ifix

        output = io.StringIO()
        with patch.object(ifix, "acquire", side_effect=OSError("permission denied")):
            with contextlib.redirect_stdout(output):
                result = ifix.main(["--data-dir", tempfile.gettempdir()])
        self.assertEqual(result, 1)
        self.assertIn("permission denied", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_cli_help_exits_without_making_a_network_request(self):
        completed = subprocess.run(
            [sys.executable, "-m", "backend.src.internet_data_getter", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Acquire historical data from registered sources", completed.stdout)
        self.assertIn("{ifix,selic}", completed.stdout)

    def test_offline_restore_command_is_available_without_downloading(self):
        from backend.src.internet_data_getter import __main__ as ifix
        with tempfile.TemporaryDirectory() as temp:
            data_root = Path(temp) / "data"
            store = FileStore(data_root)
            old = csv_bytes(2011, "TEST_FIXTURE_OLD")
            new = csv_bytes(2011, "TEST_FIXTURE_NEW")
            store.save(2011, old, datetime(2026, 11, 3, tzinfo=timezone.utc))
            store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
            manifest = json.loads(store.manifest_path.read_text("utf-8"))
            backup_ref = manifest["files"]["2011"]["previous_versions"][0]["path"]
            old_digest = hashlib.sha256(old).hexdigest()

            with patch.object(B3IfixClient, "download_year", side_effect=AssertionError("network used")):
                exit_code = ifix.main(
                    ["--data-dir", str(data_root), "restore", "--year", "2011", "--backup", backup_ref]
                )

            restored_manifest = json.loads(store.manifest_path.read_text("utf-8"))
            active = data_root / "ifix/source/IFIX_2011_Evolucao_Diaria.csv"
            self.assertEqual(exit_code, 0)
            self.assertEqual(active.read_bytes(), old)
            record = restored_manifest["files"]["2011"]
            self.assertEqual(record["sha256"], old_digest)
            self.assertEqual(record["restored_from"], backup_ref)
            self.assertEqual(len(record["previous_versions"]), 2)
            displaced = data_root / record["previous_versions"][-1]["path"]
            self.assertEqual(displaced.read_bytes(), new)

    def test_restore_cli_reports_invalid_year_as_a_command_error(self):
        from backend.src.internet_data_getter import __main__ as ifix

        with tempfile.TemporaryDirectory() as temp:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = ifix.main(
                    ["--data-dir", str(Path(temp) / "data"), "restore", "--year", "2010", "--backup", "unused.csv"]
                )
        self.assertEqual(result, 1)
        self.assertIn("2011", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
