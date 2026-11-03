import base64
import contextlib
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest.mock
import urllib.error
import unittest

from backend.src.internet_data_getter.ibovespa.b3_source import (
    B3IbovespaClient,
    DownloadError,
    available_years,
    validate_csv,
)
from backend.src.internet_data_getter.ibovespa.service import IbovespaAcquisition
from backend.src.internet_data_getter.ibovespa.storage import FileStore, LockError, ManifestError


MONTH_HEADERS = "Dia;Jan;Fev;Mar;Abr;Mai;Jun;Jul;Ago;Set;Out;Nov;Dez"


def csv_bytes(year, label="TEST_FIXTURE_NON_MARKET"):
    lines = [f"IBOV - {year}", MONTH_HEADERS]
    for day in range(1, 32):
        cells = [str(day)] + ([label] + [""] * 11 if day == 1 else [""] * 12)
        lines.append(";".join(cells))
    lines.extend([
        ";".join(["MÍNIMO", "TEST_FIXTURE_METADATA"] + [""] * 11),
        ";".join(["MÁXIMO", "TEST_FIXTURE_METADATA"] + [""] * 11),
    ])
    return ("\r\n".join(lines) + "\r\n").encode("cp1252")


class FakeResponse:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


class IbovespaSourceTests(unittest.TestCase):
    def test_years_cover_2011_through_the_current_year(self):
        self.assertEqual(available_years(2026), list(range(2011, 2027)))
        self.assertEqual(available_years(2030), list(range(2011, 2031)))
        self.assertEqual(available_years(2010), [])

    def test_client_decodes_the_b3_base64_csv_bytes_unchanged(self):
        expected = csv_bytes(2011)
        requested = []

        def opener(url, timeout):
            requested.append(url)
            self.assertGreater(timeout, 0)
            return FakeResponse(base64.b64encode(expected))

        client = B3IbovespaClient(opener=opener, sleeper=lambda _: None)
        self.assertEqual(client.download_year(2011), expected)
        self.assertEqual(len(requested), 1)
        encoded_payload = requested[0].rsplit("/", 1)[1]
        self.assertEqual(json.loads(base64.b64decode(encoded_payload)), {
            "index": "IBOV", "language": "pt-br", "year": "2011"
        })

    def test_validation_accepts_observed_current_year_shape(self):
        content = csv_bytes(2026, "TEST_FIXTURE_PARTIAL_YEAR")
        validate_csv(content, 2026)

    def test_validation_allows_duplicate_nonempty_summary_labels_seen_from_b3(self):
        lines = csv_bytes(2011).decode("cp1252").splitlines()
        lines[-1] = lines[-1].replace("MÁXIMO", "MÍNIMO")
        validate_csv(("\r\n".join(lines) + "\r\n").encode("cp1252"), 2011)

    def test_validation_rejects_wrong_year_index_truncation_and_empty_days(self):
        with self.subTest("wrong year"):
            with self.assertRaises(DownloadError):
                validate_csv(csv_bytes(2012), 2011)
        with self.subTest("wrong index"):
            with self.assertRaises(DownloadError):
                validate_csv(csv_bytes(2011).replace(b"IBOV - 2011", b"IFIX - 2011"), 2011)
        with self.subTest("truncated matrix"):
            with self.assertRaises(DownloadError):
                validate_csv(b"IBOV - 2011\r\n" + MONTH_HEADERS.encode() + b"\r\n1;TEST\r\n", 2011)
        with self.subTest("incomplete summary"):
            lines = csv_bytes(2011).decode("cp1252").splitlines()
            lines[-1] = "MÁXIMO;TEST"
            content = ("\r\n".join(lines) + "\r\n").encode("cp1252")
            with self.assertRaises(DownloadError):
                validate_csv(content, 2011)
        with self.subTest("no observations"):
            content = csv_bytes(2011).replace(b"TEST_FIXTURE_NON_MARKET", b"")
            with self.assertRaises(DownloadError):
                validate_csv(content, 2011)

    def test_validation_rejects_unterminated_quoted_field_at_eof(self):
        lines = csv_bytes(2011).decode("cp1252").splitlines()
        lines[-1] += '"unterminated'
        content = "\r\n".join(lines).encode("cp1252")
        with self.assertRaises(DownloadError):
            validate_csv(content, 2011)

    def test_validation_rejects_blank_summary_label(self):
        lines = csv_bytes(2011).decode("cp1252").splitlines()
        summary = lines[33].split(";")
        summary[0] = ""
        lines[33] = ";".join(summary)
        content = ("\r\n".join(lines) + "\r\n").encode("cp1252")
        with self.assertRaises(DownloadError):
            validate_csv(content, 2011)

    def test_client_rejects_non_base64_and_http_denials_and_paces_requests(self):
        delays = []
        denied = B3IbovespaClient(
            opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                urllib.error.HTTPError("https://b3.invalid", 403, "denied", {}, None)
            ),
            sleeper=delays.append,
            pacing_seconds=0.25,
        )
        with self.assertRaises(DownloadError):
            denied.download_year(2011)
        self.assertEqual(delays, [0.25])

        invalid = B3IbovespaClient(
            opener=lambda *_args, **_kwargs: FakeResponse(b"<html>denied</html>"),
            sleeper=lambda _: None,
        )
        with self.assertRaises(DownloadError):
            invalid.download_year(2011)


class IbovespaStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data_root = self.root / "data"
        self.store = FileStore(self.data_root)
        self.now = datetime(2026, 11, 3, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def test_saves_original_bytes_and_provenance_manifest(self):
        content = csv_bytes(2011)
        result = self.store.save(2011, content, self.now)
        active = self.data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv"
        manifest = json.loads(self.store.manifest_path.read_text("utf-8"))
        record = manifest["files"]["2011"]
        self.assertEqual(active.read_bytes(), content)
        self.assertEqual(result.status, "saved")
        self.assertEqual(record["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(record["source_filename"], "Evolucao_Diaria.csv")
        self.assertIn("/IBOV?language=pt-br", record["source_url"])
        self.assertEqual(record["period"], "2011")

    def test_unchanged_bytes_keep_active_mtime_and_do_not_create_backup(self):
        content = csv_bytes(2011)
        self.store.save(2011, content, self.now)
        active = self.data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv"
        before = active.stat().st_mtime_ns
        result = self.store.save(2011, content, datetime(2026, 11, 4, tzinfo=timezone.utc))
        self.assertEqual(result.status, "unchanged")
        self.assertEqual(active.stat().st_mtime_ns, before)
        self.assertFalse((self.data_root / "backups/ibovespa").exists())

    def test_changed_bytes_are_backed_up_and_verified_before_replace(self):
        old, new = csv_bytes(2011, "TEST_FIXTURE_OLD"), csv_bytes(2011, "TEST_FIXTURE_NEW")
        self.store.save(2011, old, self.now)
        result = self.store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
        active = self.data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv"
        backups = list((self.data_root / "backups/ibovespa/2011").glob("*.csv"))
        manifest = json.loads(self.store.manifest_path.read_text("utf-8"))
        self.assertEqual(result.status, "updated")
        self.assertEqual(active.read_bytes(), new)
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), old)
        self.assertEqual(manifest["files"]["2011"]["previous_versions"][0]["sha256"], hashlib.sha256(old).hexdigest())

    def test_backup_and_active_replace_failures_preserve_old_bytes(self):
        old, new = csv_bytes(2011, "TEST_FIXTURE_OLD"), csv_bytes(2011, "TEST_FIXTURE_NEW")
        self.store.save(2011, old, self.now)
        active = self.data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv"
        with unittest.mock.patch.object(self.store, "_write_backup", side_effect=OSError("backup failed")):
            with self.assertRaisesRegex(OSError, "backup failed"):
                self.store.save(2011, new, self.now)
        self.assertEqual(active.read_bytes(), old)

        from backend.src.internet_data_getter.ibovespa import storage as storage_ibovespa
        atomic_write = storage_ibovespa._atomic_write

        def fail_active_replace(path, content):
            if path == active:
                raise OSError("replace failed")
            atomic_write(path, content)

        with unittest.mock.patch("backend.src.internet_data_getter.ibovespa.storage._atomic_write", side_effect=fail_active_replace):
            with self.assertRaisesRegex(OSError, "replace failed"):
                self.store.save(2011, new, self.now)
        self.assertEqual(active.read_bytes(), old)
        backups = list((self.data_root / "backups/ibovespa/2011").glob("*.csv"))
        self.assertEqual([item.read_bytes() for item in backups], [old])

    def test_invalid_manifest_prevents_active_file_changes(self):
        active = self.data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv"
        active.parent.mkdir(parents=True)
        old = csv_bytes(2011, "TEST_FIXTURE_OLD")
        active.write_bytes(old)
        self.store.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.store.manifest_path.write_text("[]", encoding="utf-8")
        with self.assertRaises(ManifestError):
            self.store.save(2011, csv_bytes(2011, "TEST_FIXTURE_NEW"), self.now)
        self.assertEqual(active.read_bytes(), old)

    def test_interrupted_manifest_commit_recovers_backup_reference_on_rerun(self):
        old, new = csv_bytes(2011, "TEST_FIXTURE_OLD"), csv_bytes(2011, "TEST_FIXTURE_NEW")
        self.store.save(2011, old, self.now)
        from backend.src.internet_data_getter.ibovespa import storage as storage_ibovespa
        atomic_write = storage_ibovespa._atomic_write
        active = self.data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv"

        def fail_manifest_after_replace(path, content):
            if path == self.store.manifest_path and active.exists() and active.read_bytes() == new:
                raise OSError("manifest replace failed")
            atomic_write(path, content)

        with unittest.mock.patch("backend.src.internet_data_getter.ibovespa.storage._atomic_write", side_effect=fail_manifest_after_replace):
            with self.assertRaisesRegex(OSError, "manifest replace failed"):
                self.store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
        result = self.store.save(2011, new, datetime(2026, 11, 5, tzinfo=timezone.utc))
        manifest = json.loads(self.store.manifest_path.read_text("utf-8"))
        self.assertEqual(result.status, "unchanged")
        references = manifest["files"]["2011"]["previous_versions"]
        self.assertEqual(len(references), 1)
        backup = self.data_root / references[0]["path"]
        self.assertEqual(hashlib.sha256(backup.read_bytes()).hexdigest(), references[0]["sha256"])

    def test_first_pending_manifest_failure_does_not_orphan_update_backup(self):
        old, new = csv_bytes(2011, "TEST_FIXTURE_OLD"), csv_bytes(2011, "TEST_FIXTURE_NEW")
        self.store.save(2011, old, self.now)
        from backend.src.internet_data_getter.ibovespa import storage as storage_ibovespa
        atomic_write = storage_ibovespa._atomic_write
        failed = False

        def fail_first_pending_manifest(path, content):
            nonlocal failed
            backups = list((self.data_root / "backups/ibovespa/2011").glob("*.csv"))
            if path == self.store.manifest_path and backups and not failed:
                failed = True
                raise OSError("pending manifest write failed")
            atomic_write(path, content)

        with unittest.mock.patch(
            "backend.src.internet_data_getter.ibovespa.storage._atomic_write",
            side_effect=fail_first_pending_manifest,
        ):
            with self.assertRaisesRegex(OSError, "pending manifest write failed"):
                self.store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
        active = self.data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv"
        self.assertEqual(active.read_bytes(), old)

        self.store.save(2011, new, datetime(2026, 11, 5, tzinfo=timezone.utc))
        backups = list((self.data_root / "backups/ibovespa/2011").glob("*.csv"))
        manifest = json.loads(self.store.manifest_path.read_text("utf-8"))
        references = manifest["files"]["2011"]["previous_versions"]
        self.assertEqual(len(backups), 1)
        self.assertEqual([self.data_root / item["path"] for item in references], backups)

    def test_first_pending_manifest_failure_does_not_orphan_restore_backup(self):
        old, new = csv_bytes(2011, "TEST_FIXTURE_OLD"), csv_bytes(2011, "TEST_FIXTURE_NEW")
        self.store.save(2011, old, self.now)
        self.store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
        manifest = json.loads(self.store.manifest_path.read_text("utf-8"))
        restore_ref = manifest["files"]["2011"]["previous_versions"][0]["path"]
        from backend.src.internet_data_getter.ibovespa import storage as storage_ibovespa
        atomic_write = storage_ibovespa._atomic_write
        failed = False

        def fail_first_pending_manifest(path, content):
            nonlocal failed
            backups = list((self.data_root / "backups/ibovespa/2011").glob("*.csv"))
            if path == self.store.manifest_path and len(backups) == 2 and not failed:
                failed = True
                raise OSError("restore pending manifest write failed")
            atomic_write(path, content)

        with unittest.mock.patch(
            "backend.src.internet_data_getter.ibovespa.storage._atomic_write",
            side_effect=fail_first_pending_manifest,
        ):
            with self.assertRaisesRegex(OSError, "restore pending manifest write failed"):
                self.store.restore(2011, restore_ref, datetime(2026, 11, 5, tzinfo=timezone.utc))
        active = self.data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv"
        self.assertEqual(active.read_bytes(), new)

        self.store.restore(2011, restore_ref, datetime(2026, 11, 6, tzinfo=timezone.utc))
        backups = list((self.data_root / "backups/ibovespa/2011").glob("*.csv"))
        manifest = json.loads(self.store.manifest_path.read_text("utf-8"))
        references = manifest["files"]["2011"]["previous_versions"]
        self.assertEqual(len(backups), 2)
        self.assertEqual({self.data_root / item["path"] for item in references}, set(backups))

    def test_offline_restore_verifies_backup_and_preserves_displaced_active(self):
        old, new = csv_bytes(2011, "TEST_FIXTURE_OLD"), csv_bytes(2011, "TEST_FIXTURE_NEW")
        self.store.save(2011, old, self.now)
        self.store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
        manifest = json.loads(self.store.manifest_path.read_text("utf-8"))
        backup_ref = manifest["files"]["2011"]["previous_versions"][0]["path"]
        result = self.store.restore(2011, backup_ref, datetime(2026, 11, 5, tzinfo=timezone.utc))
        active = self.data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv"
        restored = json.loads(self.store.manifest_path.read_text("utf-8"))["files"]["2011"]
        self.assertEqual(result.status, "restored")
        self.assertEqual(active.read_bytes(), old)
        self.assertEqual(restored["restored_from"], backup_ref)
        displaced = self.data_root / restored["previous_versions"][-1]["path"]
        self.assertEqual(displaced.read_bytes(), new)

    def test_corrupt_backup_is_rejected_without_changing_active(self):
        old, new = csv_bytes(2011, "TEST_FIXTURE_OLD"), csv_bytes(2011, "TEST_FIXTURE_NEW")
        self.store.save(2011, old, self.now)
        self.store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
        manifest = json.loads(self.store.manifest_path.read_text("utf-8"))
        backup_ref = manifest["files"]["2011"]["previous_versions"][0]["path"]
        (self.data_root / backup_ref).write_bytes(b"corrupt backup")
        active = self.data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv"
        with self.assertRaises(ManifestError):
            self.store.restore(2011, backup_ref, datetime(2026, 11, 5, tzinfo=timezone.utc))
        self.assertEqual(active.read_bytes(), new)

    def test_lock_rejects_overlapping_operation(self):
        with self.store.lock():
            with self.assertRaises(LockError):
                with self.store.lock():
                    pass


class IbovespaServiceTests(unittest.TestCase):
    def test_partial_source_error_is_reported_and_other_years_are_saved(self):
        class Client:
            def download_year(self, year):
                if year == 2012:
                    raise DownloadError("source unavailable")
                return csv_bytes(year)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data"
            result = IbovespaAcquisition(Client(), FileStore(root), current_year=2013).run(
                now=datetime(2026, 11, 3, tzinfo=timezone.utc)
            )
            self.assertFalse(result.complete)
            self.assertEqual(result.errors, {2012: "source unavailable"})
            self.assertTrue((root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv").exists())
            self.assertTrue((root / "ibovespa/source/IBOVESPA_2013_Evolucao_Diaria.csv").exists())

    def test_no_year_range_is_reported_incomplete_without_network(self):
        class UnusedClient:
            def download_year(self, year):
                raise AssertionError("no request should be made")

        with tempfile.TemporaryDirectory() as temp:
            result = IbovespaAcquisition(UnusedClient(), FileStore(Path(temp) / "data"), 2010).run()
        self.assertFalse(result.complete)
        self.assertIn("discovery", result.errors)

    def test_ibovespa_run_does_not_change_existing_ifix_files(self):
        class Client:
            def download_year(self, year):
                return csv_bytes(year)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data"
            ifix_file = root / "ifix/source/IFIX_2011_Evolucao_Diaria.csv"
            ifix_manifest = root / "ifix/manifest.json"
            ifix_backup = root / "backups/ifix/2011/known.csv"
            ifix_file.parent.mkdir(parents=True)
            ifix_backup.parent.mkdir(parents=True)
            ifix_file.write_bytes(b"existing IFIX source sentinel")
            ifix_manifest.write_bytes(b"existing IFIX manifest sentinel")
            ifix_backup.write_bytes(b"existing IFIX backup sentinel")
            result = IbovespaAcquisition(Client(), FileStore(root), current_year=2011).run(
                now=datetime(2026, 11, 3, tzinfo=timezone.utc)
            )
            self.assertTrue(result.complete)
            self.assertEqual(ifix_file.read_bytes(), b"existing IFIX source sentinel")
            self.assertEqual(ifix_manifest.read_bytes(), b"existing IFIX manifest sentinel")
            self.assertEqual(ifix_backup.read_bytes(), b"existing IFIX backup sentinel")

    def test_overlapping_service_run_fails_before_requesting_source_years(self):
        class Client:
            def download_year(self, year):
                raise AssertionError("source request must not start while lock is held")

        with tempfile.TemporaryDirectory() as temp:
            store = FileStore(Path(temp) / "data")
            acquisition = IbovespaAcquisition(Client(), store, current_year=2011)
            with store.lock():
                with self.assertRaises(LockError):
                    acquisition.run()

    def test_cli_has_distinct_offline_restore_command(self):
        from backend.src.internet_data_getter import __main__ as getter_cli

        with tempfile.TemporaryDirectory() as temp:
            data_root = Path(temp) / "data"
            store = FileStore(data_root)
            old, new = csv_bytes(2011, "TEST_FIXTURE_OLD"), csv_bytes(2011, "TEST_FIXTURE_NEW")
            store.save(2011, old, datetime(2026, 11, 3, tzinfo=timezone.utc))
            store.save(2011, new, datetime(2026, 11, 4, tzinfo=timezone.utc))
            backup_ref = json.loads(store.manifest_path.read_text("utf-8"))["files"]["2011"]["previous_versions"][0]["path"]
            with unittest.mock.patch.object(B3IbovespaClient, "download_year", side_effect=AssertionError("network used")):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = getter_cli.main([
                        "--data-dir", str(data_root), "restore-ibovespa",
                        "--year", "2011", "--backup", backup_ref,
                    ])
            self.assertEqual(code, 0)
            self.assertEqual((data_root / "ibovespa/source/IBOVESPA_2011_Evolucao_Diaria.csv").read_bytes(), old)


if __name__ == "__main__":
    unittest.main()
