"""Transactional CSV and provenance storage for S&P 500 observations."""
from __future__ import annotations

import contextlib
from copy import deepcopy
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import tempfile
from typing import Iterator
import uuid

from .source import (
    Observation,
    PageResult,
    SOURCE_URL,
    SourceError,
    validate_history_request_url,
)


_HASH = re.compile(r"^[0-9a-f]{64}$")
_CSV_HEADER = "date,adjusted_close"
_PRICE = re.compile(r"^\d+(?:\.\d+)?$")
_FORMAT = "UTF-8 CSV; ISO dates; decimal point; Yahoo Adj Close displayed precision"
_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def csv_bytes(observations: tuple[Observation, ...]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow((_CSV_HEADER.split(",")))
    writer.writerows((item.date.isoformat(), item.adjusted_close) for item in observations)
    return output.getvalue().encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as stream:
            temporary = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


class StoreError(OSError):
    """The active dataset cannot be safely read or updated."""


class LockError(StoreError):
    """An S&P 500 acquisition or restore already owns the data directory."""


class ManifestError(StoreError):
    """Stored S&P 500 provenance is invalid."""


class RestoreError(StoreError):
    """The requested backup is not listed or fails verification."""


class Sp500FileStore:
    """Keep a single active CSV paired with validated provenance and backups."""

    def __init__(self, data_root: Path | str):
        self.data_root = Path(data_root)
        self.asset_root = self.data_root / "sp500"
        self.active_root = self.asset_root / "source"
        self.active_path = self.active_root / "sp500_yahoo.csv"
        self.manifest_path = self.asset_root / "manifest.json"
        self.pending_path = self.asset_root / ".pending-update.json"
        self.lock_path = self.asset_root / ".acquisition.lock"
        self.backup_root = self.data_root / "backups" / "sp500"

    @contextlib.contextmanager
    def lock(self):
        self.asset_root.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise LockError(
                f"another S&P 500 operation is running (or a stale lock remains at {self.lock_path}); "
                "confirm no operation is active before removing a stale lock"
            ) from exc
        try:
            content = f"pid={os.getpid()}\ncreated_at={utc_timestamp(datetime.now(timezone.utc))}\n"
            os.write(fd, content.encode("utf-8"))
            os.fsync(fd)
            yield
        finally:
            os.close(fd)
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass

    def _manifest_bytes(self, manifest: dict) -> bytes:
        return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

    @staticmethod
    def _parse_csv(content: bytes, error_type=ManifestError) -> tuple[Observation, ...]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise error_type("S&P 500 CSV is not UTF-8") from exc
        try:
            rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
        except csv.Error as exc:
            raise error_type("S&P 500 CSV contains malformed quoting") from exc
        if not rows or rows[0] != ["date", "adjusted_close"]:
            raise error_type("S&P 500 CSV does not have the expected header")
        observations: list[Observation] = []
        for row in rows[1:]:
            if len(row) != 2:
                raise error_type("S&P 500 CSV contains a malformed observation row")
            try:
                day = date.fromisoformat(row[0])
            except ValueError as exc:
                raise error_type("S&P 500 CSV contains an invalid ISO date") from exc
            if day.isoformat() != row[0] or not _PRICE.fullmatch(row[1]):
                raise error_type("S&P 500 CSV contains a noncanonical date or price")
            observations.append(Observation(day, row[1]))
        if not observations:
            raise error_type("S&P 500 CSV contains no observations")
        if any(later.date <= earlier.date for earlier, later in zip(observations, observations[1:])):
            raise error_type("S&P 500 CSV observations are duplicated or out of order")
        if csv_bytes(tuple(observations)) != content:
            raise error_type("S&P 500 CSV bytes are not in canonical format")
        return tuple(observations)

    def _resolve_backup(self, relative: str) -> Path:
        if not isinstance(relative, str) or "\\" in relative:
            raise RestoreError("S&P 500 backup path must be a manifest-listed relative path")
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or len(pure.parts) != 3
            or pure.parts[:2] != ("backups", "sp500")
            or pure.suffix.lower() not in {".csv", ".json"}
        ):
            raise RestoreError("S&P 500 backup path is outside backups/sp500")
        target = (self.data_root / Path(*pure.parts)).resolve()
        scope = self.backup_root.resolve()
        try:
            if os.path.commonpath((str(scope), str(target))) != str(scope):
                raise RestoreError("S&P 500 backup path escapes backups/sp500")
        except ValueError as exc:
            raise RestoreError("S&P 500 backup path is on a different drive") from exc
        return target

    @staticmethod
    def _validate_timestamp(value, error_type=ManifestError) -> None:
        if not isinstance(value, str) or not _UTC_TIMESTAMP.fullmatch(value):
            raise error_type("S&P 500 manifest has an invalid UTC timestamp")
        try:
            datetime.fromisoformat(value[:-1] + "+00:00")
        except ValueError as exc:
            raise error_type("S&P 500 manifest has an invalid UTC timestamp") from exc

    def _validate_manifest(self, manifest) -> None:
        if (
            not isinstance(manifest, dict)
            or type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != 1
        ):
            raise ManifestError("S&P 500 manifest has an unsupported schema")
        if manifest.get("source_url") != SOURCE_URL or manifest.get("symbol") != "^GSPC":
            raise ManifestError("S&P 500 manifest has an unexpected source or symbol")
        if manifest.get("format") != _FORMAT:
            raise ManifestError("S&P 500 manifest has an unexpected CSV format")
        current = manifest.get("current")
        if not isinstance(current, dict):
            raise ManifestError("S&P 500 manifest has no current record")
        required = (
            "retrieved_at", "requested_start", "requested_end", "first_date", "last_date",
            "observation_count", "sha256", "requested_windows", "previous_versions",
        )
        if any(key not in current for key in required):
            raise ManifestError("S&P 500 manifest current record is incomplete")
        self._validate_timestamp(current["retrieved_at"])
        date_fields = ("requested_start", "requested_end", "first_date", "last_date")
        for key in date_fields:
            value = current[key]
            try:
                parsed = date.fromisoformat(value)
            except (TypeError, ValueError) as exc:
                raise ManifestError(f"S&P 500 manifest has an invalid {key}") from exc
            if parsed.isoformat() != value:
                raise ManifestError(f"S&P 500 manifest has a noncanonical {key}")
        if current["requested_start"] > current["requested_end"] or current["first_date"] > current["last_date"]:
            raise ManifestError("S&P 500 manifest date coverage is reversed")
        if type(current["observation_count"]) is not int or current["observation_count"] < 1:
            raise ManifestError("S&P 500 manifest has an invalid observation count")
        if not isinstance(current["sha256"], str) or not _HASH.fullmatch(current["sha256"]):
            raise ManifestError("S&P 500 manifest has an invalid CSV digest")
        if not isinstance(current["requested_windows"], list) or not current["requested_windows"]:
            raise ManifestError("S&P 500 manifest requested_windows must be a nonempty list")
        window_ranges: list[tuple[date, date]] = []
        for window in current["requested_windows"]:
            if not isinstance(window, dict):
                raise ManifestError("S&P 500 manifest has an invalid request window")
            try:
                start, end = date.fromisoformat(window["start"]), date.fromisoformat(window["end"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ManifestError("S&P 500 manifest has an invalid request window") from exc
            if start.isoformat() != window["start"] or end.isoformat() != window["end"] or start > end:
                raise ManifestError("S&P 500 manifest request window is reversed or noncanonical")
            try:
                validate_history_request_url(window.get("source_url"), start, end)
            except SourceError as exc:
                raise ManifestError("S&P 500 manifest request URL does not match its date window") from exc
            window_ranges.append((start, end))
        if (
            min(start for start, _end in window_ranges).isoformat() != current["requested_start"]
            or max(end for _start, end in window_ranges).isoformat() != current["requested_end"]
        ):
            raise ManifestError("S&P 500 requested bounds do not match its request windows")
        references = current["previous_versions"]
        if not isinstance(references, list):
            raise ManifestError("S&P 500 manifest previous_versions must be a list")
        for reference in references:
            if not isinstance(reference, dict):
                raise ManifestError("S&P 500 manifest has an invalid backup reference")
            for field in ("csv_path", "manifest_path"):
                self._resolve_backup(reference.get(field))
            for field in ("csv_sha256", "manifest_sha256"):
                if not isinstance(reference.get(field), str) or not _HASH.fullmatch(reference[field]):
                    raise ManifestError("S&P 500 manifest backup reference has an invalid digest")
        if "restored_at" in current:
            self._validate_timestamp(current["restored_at"])

    def _validate_pair(self, manifest: dict, content: bytes) -> tuple[Observation, ...]:
        self._validate_manifest(manifest)
        current = manifest["current"]
        if sha256(content) != current["sha256"]:
            raise ManifestError("S&P 500 manifest hash does not match its CSV")
        observations = self._parse_csv(content)
        if len(observations) != current["observation_count"]:
            raise ManifestError("S&P 500 manifest observation count does not match its CSV")
        if (
            observations[0].date.isoformat() != current["first_date"]
            or observations[-1].date.isoformat() != current["last_date"]
        ):
            raise ManifestError("S&P 500 manifest coverage does not match its CSV")
        return observations

    def _read_manifest(self) -> dict | None:
        if not self.manifest_path.exists():
            return None
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"cannot read S&P 500 manifest: {exc}") from exc
        self._validate_manifest(manifest)
        return manifest

    def _read_current(self) -> tuple[tuple[Observation, ...], dict, bytes] | None:
        csv_exists, manifest_exists = self.active_path.exists(), self.manifest_path.exists()
        if not csv_exists and not manifest_exists:
            return None
        if not csv_exists or not manifest_exists:
            raise ManifestError("S&P 500 active CSV and provenance manifest must exist together")
        try:
            content = self.active_path.read_bytes()
        except OSError as exc:
            raise ManifestError(f"cannot read S&P 500 CSV: {exc}") from exc
        manifest = self._read_manifest()
        assert manifest is not None
        return self._validate_pair(manifest, content), manifest, content

    def _backup_pair(self, csv_content: bytes, manifest_content: bytes, now: datetime) -> dict:
        timestamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        csv_hash, manifest_hash = sha256(csv_content), sha256(manifest_content)
        stem = f"{timestamp}-{csv_hash}-{uuid.uuid4().hex[:8]}"
        csv_path = self.backup_root / f"{stem}.csv"
        manifest_path = self.backup_root / f"{stem}.manifest.json"
        _atomic_write(csv_path, csv_content)
        _atomic_write(manifest_path, manifest_content)
        if sha256(csv_path.read_bytes()) != csv_hash or sha256(manifest_path.read_bytes()) != manifest_hash:
            raise StoreError("S&P 500 backup verification failed")
        return {
            "csv_path": csv_path.relative_to(self.data_root).as_posix(),
            "csv_sha256": csv_hash,
            "manifest_path": manifest_path.relative_to(self.data_root).as_posix(),
            "manifest_sha256": manifest_hash,
        }

    def _read_backup_pair(self, reference: dict) -> tuple[dict, bytes, tuple[Observation, ...]]:
        try:
            csv_content = self._resolve_backup(reference["csv_path"]).read_bytes()
            manifest_content = self._resolve_backup(reference["manifest_path"]).read_bytes()
        except OSError as exc:
            raise RestoreError("cannot read S&P 500 backup pair") from exc
        if sha256(csv_content) != reference["csv_sha256"]:
            raise RestoreError("S&P 500 CSV backup hash does not match its manifest")
        if sha256(manifest_content) != reference["manifest_sha256"]:
            raise RestoreError("S&P 500 manifest backup hash does not match its reference")
        try:
            historical_manifest = json.loads(manifest_content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RestoreError("S&P 500 backup manifest is invalid") from exc
        observations = self._validate_pair(historical_manifest, csv_content)
        return historical_manifest, csv_content, observations

    def _append_backup(self, manifest: dict, reference: dict | None) -> None:
        if reference is None:
            return
        previous = manifest["current"].setdefault("previous_versions", [])
        if not any(item.get("csv_path") == reference["csv_path"] for item in previous):
            previous.append(reference)

    def _commit_locked(
        self,
        content: bytes,
        new_manifest: dict,
        old_pair: tuple[tuple[Observation, ...], dict, bytes] | None,
        now: datetime,
    ) -> dict:
        old_manifest_content = self.manifest_path.read_bytes() if old_pair else None
        backup = self._backup_pair(old_pair[2], old_manifest_content, now) if old_pair else None
        self._append_backup(new_manifest, backup)
        self._validate_manifest(new_manifest)
        new_manifest_content = self._manifest_bytes(new_manifest)
        new_csv_hash, new_manifest_hash = sha256(content), sha256(new_manifest_content)

        rollback_manifest = deepcopy(old_pair[1]) if old_pair else None
        if rollback_manifest is not None:
            self._append_backup(rollback_manifest, backup)
        rollback_bytes = self._manifest_bytes(rollback_manifest) if rollback_manifest else None
        pending = {
            "old_csv_sha256": sha256(old_pair[2]) if old_pair else None,
            "old_manifest_sha256": sha256(old_manifest_content) if old_manifest_content else None,
            "new_csv_sha256": new_csv_hash,
            "new_manifest_sha256": new_manifest_hash,
            "new_manifest": new_manifest,
            "rollback_manifest": rollback_manifest,
            "rollback_manifest_sha256": sha256(rollback_bytes) if rollback_bytes else None,
            "backup": backup,
        }
        _atomic_write(self.pending_path, json.dumps(pending, ensure_ascii=False, indent=2).encode("utf-8"))
        _atomic_write(self.active_path, content)
        _atomic_write(self.manifest_path, new_manifest_content)
        self.pending_path.unlink()
        return {
            "status": "saved" if old_pair is None else "updated",
            "sha256": new_csv_hash,
            "path": self.active_path,
            "manifest": new_manifest,
        }

    def recover_locked(self) -> None:
        if not self.pending_path.exists():
            return
        try:
            pending = json.loads(self.pending_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"cannot read S&P 500 write-ahead record: {exc}") from exc
        if not isinstance(pending, dict):
            raise ManifestError("S&P 500 write-ahead record is invalid")
        self._validate_manifest(pending.get("new_manifest"))
        new_manifest = pending["new_manifest"]
        new_manifest_content = self._manifest_bytes(new_manifest)
        new_csv_hash = pending.get("new_csv_sha256")
        if new_manifest["current"]["sha256"] != new_csv_hash or sha256(new_manifest_content) != pending.get("new_manifest_sha256"):
            raise ManifestError("S&P 500 write-ahead record disagrees with the new manifest")
        old_csv_hash = pending.get("old_csv_sha256")
        old_manifest_hash = pending.get("old_manifest_sha256")
        for value in (new_csv_hash, old_csv_hash, old_manifest_hash):
            if value is not None and (not isinstance(value, str) or not _HASH.fullmatch(value)):
                raise ManifestError("S&P 500 write-ahead record has an invalid digest")
        rollback = pending.get("rollback_manifest")
        rollback_content = self._manifest_bytes(rollback) if rollback else None
        if rollback is not None:
            self._validate_manifest(rollback)
            if sha256(rollback_content) != pending.get("rollback_manifest_sha256"):
                raise ManifestError("S&P 500 write-ahead rollback manifest is invalid")
        required_pending = (
            "old_csv_sha256", "old_manifest_sha256", "new_csv_sha256", "new_manifest_sha256",
            "new_manifest", "rollback_manifest", "rollback_manifest_sha256", "backup",
        )
        if any(key not in pending for key in required_pending):
            raise ManifestError("S&P 500 write-ahead record is incomplete")
        has_old_csv = old_csv_hash is not None
        has_old_manifest = old_manifest_hash is not None
        if has_old_csv != has_old_manifest:
            raise ManifestError("S&P 500 write-ahead old-pair hashes are incomplete")
        rollback_hash = pending["rollback_manifest_sha256"]
        if has_old_csv:
            if (
                not isinstance(rollback, dict)
                or not isinstance(rollback_hash, str)
                or not _HASH.fullmatch(rollback_hash)
                or rollback["current"]["sha256"] != old_csv_hash
            ):
                raise ManifestError("S&P 500 write-ahead rollback version is missing or inconsistent")
        elif rollback is not None or rollback_hash is not None:
            raise ManifestError("S&P 500 write-ahead record has a rollback without a prior active pair")
        backup = pending["backup"]
        prior_backup_manifest = None
        backup_csv = None
        if has_old_csv:
            if not isinstance(backup, dict):
                raise ManifestError("S&P 500 write-ahead record is missing its prior backup pair")
            backup_fields = ("csv_path", "manifest_path", "csv_sha256", "manifest_sha256")
            if any(key not in backup for key in backup_fields):
                raise ManifestError("S&P 500 write-ahead backup metadata is incomplete")
            if backup["csv_sha256"] != old_csv_hash or backup["manifest_sha256"] != old_manifest_hash:
                raise ManifestError("S&P 500 write-ahead backup hashes do not match the old pair")
            try:
                prior_backup_manifest, backup_csv, _backup_observations = self._read_backup_pair(backup)
                backup_manifest_content = self._resolve_backup(backup["manifest_path"]).read_bytes()
            except (StoreError, KeyError, TypeError, OSError) as exc:
                raise ManifestError("S&P 500 write-ahead prior backup pair is unavailable or invalid") from exc
            if sha256(backup_csv) != old_csv_hash or sha256(backup_manifest_content) != old_manifest_hash:
                raise ManifestError("S&P 500 write-ahead prior backup does not match the old pair hashes")
            self._validate_pair(rollback, backup_csv)
        elif backup is not None:
            raise ManifestError("S&P 500 write-ahead record has a backup without a prior active pair")

        try:
            active_content = self.active_path.read_bytes() if self.active_path.exists() else None
            active_manifest_content = self.manifest_path.read_bytes() if self.manifest_path.exists() else None
        except OSError as exc:
            raise ManifestError(f"cannot read S&P 500 files during recovery: {exc}") from exc
        active_hash = sha256(active_content) if active_content is not None else None
        manifest_hash = sha256(active_manifest_content) if active_manifest_content is not None else None
        if active_hash == new_csv_hash:
            assert active_content is not None
            self._validate_pair(new_manifest, active_content)
            if manifest_hash == pending["new_manifest_sha256"]:
                self.pending_path.unlink()
                return
            if manifest_hash == old_manifest_hash:
                _atomic_write(self.manifest_path, new_manifest_content)
                self.pending_path.unlink()
                return
        if active_hash == old_csv_hash:
            if manifest_hash == old_manifest_hash:
                if has_old_csv:
                    assert active_content is not None and prior_backup_manifest is not None
                    self._validate_pair(prior_backup_manifest, active_content)
                    self._validate_pair(rollback, active_content)
                if rollback_content is not None and sha256(rollback_content) != old_manifest_hash:
                    _atomic_write(self.manifest_path, rollback_content)
                self.pending_path.unlink()
                return
            if rollback is not None and manifest_hash == pending["rollback_manifest_sha256"]:
                assert active_content is not None
                self._validate_pair(rollback, active_content)
                self.pending_path.unlink()
                return
            if not has_old_csv and manifest_hash is None:
                self.pending_path.unlink()
                return
        raise ManifestError(
            "S&P 500 active CSV and manifest match neither known transaction state; "
            "the pending record was preserved"
        )

    def load_locked(self) -> tuple[Observation, ...]:
        self.recover_locked()
        current = self._read_current()
        return current[0] if current else ()

    def load(self) -> tuple[Observation, ...]:
        with self.lock():
            return self.load_locked()

    def save_locked(
        self,
        observations: tuple[Observation, ...],
        requested_windows: tuple[PageResult, ...],
        now: datetime,
    ) -> dict:
        self.recover_locked()
        parsed_observations = tuple(observations)
        if not parsed_observations:
            raise StoreError("cannot save an S&P 500 dataset without observations")
        content = csv_bytes(parsed_observations)
        canonical_observations = self._parse_csv(content, StoreError)
        old_pair = self._read_current()
        digest = sha256(content)
        timestamp = utc_timestamp(now)
        windows = [
            {
                "start": page.start_date.isoformat(),
                "end": page.end_date.isoformat(),
                "source_url": page.source_url,
            }
            for page in requested_windows
        ]
        if not windows:
            raise StoreError("S&P 500 provenance requires at least one source request window")
        if old_pair and old_pair[1]["current"]["sha256"] == digest:
            return {
                "status": "unchanged", "sha256": digest, "path": self.active_path,
                "manifest": old_pair[1],
            }

        record = {
            "retrieved_at": timestamp,
            "requested_start": min(item.start_date for item in requested_windows).isoformat(),
            "requested_end": max(item.end_date for item in requested_windows).isoformat(),
            "requested_windows": windows,
            "first_date": canonical_observations[0].date.isoformat(),
            "last_date": canonical_observations[-1].date.isoformat(),
            "observation_count": len(canonical_observations),
            "sha256": digest,
            "previous_versions": deepcopy(old_pair[1]["current"].get("previous_versions", [])) if old_pair else [],
        }
        manifest = {
            "schema_version": 1,
            "source_url": SOURCE_URL,
            "symbol": "^GSPC",
            "format": _FORMAT,
            "current": record,
        }
        if old_pair and "last_checked_at" in old_pair[1]:
            manifest["last_checked_at"] = old_pair[1]["last_checked_at"]
            manifest["last_checked_windows"] = old_pair[1].get("last_checked_windows", [])
        return self._commit_locked(content, manifest, old_pair, now)

    def save(
        self,
        observations: tuple[Observation, ...],
        requested_windows: tuple[PageResult, ...],
        now: datetime,
    ) -> dict:
        with self.lock():
            return self.save_locked(observations, requested_windows, now)

    def restore_locked(self, backup_path: str, now: datetime) -> dict:
        self.recover_locked()
        current_pair = self._read_current()
        if current_pair is None:
            raise RestoreError("no active S&P 500 manifest is available")
        current_manifest = current_pair[1]
        reference = next(
            (
                item for item in current_manifest["current"]["previous_versions"]
                if backup_path in (item["csv_path"], item["manifest_path"])
            ),
            None,
        )
        if reference is None:
            raise RestoreError("S&P 500 backup is not listed in previous_versions")
        self._resolve_backup(backup_path)
        historical_manifest, content, observations = self._read_backup_pair(reference)
        restored_manifest = deepcopy(historical_manifest)
        restored_manifest["current"]["previous_versions"] = deepcopy(
            current_manifest["current"]["previous_versions"]
        )
        restored_manifest["current"]["restored_at"] = utc_timestamp(now)
        return self._commit_locked(content, restored_manifest, current_pair, now)

    def restore(self, backup_path: str, now: datetime) -> dict:
        with self.lock():
            return self.restore_locked(backup_path, now)
