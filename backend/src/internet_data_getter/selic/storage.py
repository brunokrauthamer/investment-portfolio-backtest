"""Transactional storage, backup and offline restore for the Selic CSV."""
from __future__ import annotations

import contextlib
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Iterator
import uuid

from .source import DATASET_URL, Observation, SourceError, SourceResult, validate_observations


SOURCE_URL = (
    "https://www3.bcb.gov.br/sgspub/consultarvalores/"
    "consultarValoresSeries.do?method=consultarGraficoPorId&hdOidSeriesSelecionadas=11"
)
_HASH = re.compile(r"^[0-9a-f]{64}$")
_CSV_HEADER = "date,rate_percent_per_day\n"
_CSV_RATE = re.compile(r"^\d+(?:\.\d+)?$")
_CSV_FORMAT = "UTF-8 CSV; ISO dates; decimal point; rate is percent per day as displayed by BCB"
_BCB_LICENSE = "Open Data Commons Open Database License (ODbL)"
_REQUESTED_START = "2011-01-01"


class StoreError(OSError):
    """Active Selic files cannot be read or safely updated."""


class LockError(StoreError):
    """A Selic acquisition or restore already owns the data directory."""


class ManifestError(StoreError):
    """Selic provenance is invalid or cannot be safely recovered."""


class RestoreError(StoreError):
    """Requested Selic backup is not listed or fails verification."""


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def csv_bytes(observations: tuple[Observation, ...]) -> bytes:
    lines = [_CSV_HEADER]
    lines.extend(f"{item.date.isoformat()},{item.rate}\n" for item in observations)
    return "".join(lines).encode("utf-8")


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


class SelicFileStore:
    """Keep one active UTF-8 CSV with verified backups and a recovery record."""

    def __init__(self, data_root: Path | str):
        self.data_root = Path(data_root)
        self.root = self.data_root / "selic"
        self.active_root = self.root / "source"
        self.active_path = self.active_root / "selic_sgs_11.csv"
        self.manifest_path = self.root / "manifest.json"
        self.pending_path = self.root / ".pending-update.json"
        self.lock_path = self.root / ".acquisition.lock"
        self.backup_root = self.data_root / "backups" / "selic"

    @contextlib.contextmanager
    def lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise LockError(
                f"another operation is running (or a stale lock remains at {self.lock_path}); "
                "confirm no operation is active before removing a stale lock"
            ) from exc
        try:
            os.write(fd, f"pid={os.getpid()}\ncreated_at={utc_timestamp(datetime.now(timezone.utc))}\n".encode())
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

    def _read_manifest(self) -> dict | None:
        if not self.manifest_path.exists():
            return None
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"cannot read Selic manifest: {exc}") from exc
        self._validate_manifest(manifest)
        return manifest

    @staticmethod
    def _validate_manifest(manifest) -> None:
        if (
            not isinstance(manifest, dict)
            or type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != 1
        ):
            raise ManifestError("Selic manifest has an unsupported schema")
        if (
            manifest.get("source_url") != SOURCE_URL
            or manifest.get("dataset_url") != DATASET_URL
            or type(manifest.get("series_id")) is not int
            or manifest["series_id"] != 11
        ):
            raise ManifestError("Selic manifest has an unexpected source or series")
        if manifest.get("unit") != UNIT_FOR_MANIFEST:
            raise ManifestError("Selic manifest has a missing or unexpected unit")
        if manifest.get("license_listed_by_bcb") != _BCB_LICENSE:
            raise ManifestError("Selic manifest has missing or unexpected BCB license information")
        current = manifest.get("current")
        if not isinstance(current, dict):
            raise ManifestError("Selic manifest has no current record")
        for field in ("retrieved_at", "requested_start", "requested_end", "first_date", "last_date", "format"):
            if field not in current:
                raise ManifestError(f"Selic manifest current record is missing {field}")
        if current["format"] != _CSV_FORMAT:
            raise ManifestError("Selic manifest has missing or unexpected CSV format provenance")
        retrieved_at = current.get("retrieved_at")
        if not isinstance(retrieved_at, str):
            raise ManifestError("Selic manifest has an invalid retrieval time")
        try:
            parsed_retrieval = datetime.fromisoformat(retrieved_at[:-1] + "+00:00")
        except ValueError as exc:
            raise ManifestError("Selic manifest has an invalid retrieval time") from exc
        if not retrieved_at.endswith("Z") or utc_timestamp(parsed_retrieval) != retrieved_at:
            raise ManifestError("Selic manifest retrieval time must be canonical UTC")
        if "restored_at" in current:
            restored_at = current["restored_at"]
            if not isinstance(restored_at, str):
                raise ManifestError("Selic manifest has an invalid restore time")
            try:
                parsed_restore = datetime.fromisoformat(restored_at[:-1] + "+00:00")
            except ValueError as exc:
                raise ManifestError("Selic manifest has an invalid restore time") from exc
            if not restored_at.endswith("Z") or utc_timestamp(parsed_restore) != restored_at:
                raise ManifestError("Selic manifest restore time must be canonical UTC")
        dates = {}
        for field in ("requested_start", "requested_end", "first_date", "last_date"):
            value = current.get(field)
            if not isinstance(value, str):
                raise ManifestError(f"Selic manifest has an invalid {field}")
            try:
                parsed = date.fromisoformat(value)
            except ValueError as exc:
                raise ManifestError(f"Selic manifest has an invalid {field}") from exc
            if parsed.isoformat() != value:
                raise ManifestError(f"Selic manifest has a noncanonical {field}")
            dates[field] = parsed
        if current["requested_start"] != _REQUESTED_START:
            raise ManifestError("Selic manifest requested start is not 2011-01-01")
        if dates["first_date"].year != 2011 or dates["first_date"] > dates["last_date"]:
            raise ManifestError("Selic manifest has inconsistent observed date coverage")
        if dates["requested_end"] != dates["last_date"]:
            raise ManifestError("Selic manifest requested end does not match its last date")
        for field in ("reported_count", "observation_count"):
            if type(current.get(field)) is not int or current[field] < 1:
                raise ManifestError(f"Selic manifest has an invalid {field}")
        if current["reported_count"] != current["observation_count"]:
            raise ManifestError("Selic manifest reported and acquired counts differ")
        if not isinstance(current.get("sha256"), str) or not _HASH.fullmatch(current["sha256"]):
            raise ManifestError("Selic manifest has an invalid current CSV hash")
        if not isinstance(current.get("previous_versions"), list):
            raise ManifestError("Selic manifest previous_versions must be a list")
        for backup in current["previous_versions"]:
            if not isinstance(backup, dict):
                raise ManifestError("Selic manifest has an invalid backup reference")
            for key in ("csv_path", "manifest_path"):
                if not isinstance(backup.get(key), str):
                    raise ManifestError("Selic manifest backup path is invalid")
            for key in ("csv_sha256", "manifest_sha256"):
                if not isinstance(backup.get(key), str) or not _HASH.fullmatch(backup[key]):
                    raise ManifestError("Selic manifest backup hash is invalid")

    @staticmethod
    def _parse_csv_content(content: bytes, error_type=ManifestError) -> tuple[Observation, ...]:
        try:
            lines = content.decode("utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise error_type("Selic CSV is not UTF-8") from exc
        if not lines or lines[0] != _CSV_HEADER.rstrip("\n"):
            raise error_type("Selic CSV does not have the expected header")
        observations = []
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) != 2:
                raise error_type("Selic CSV contains a malformed observation row")
            try:
                observation_date = date.fromisoformat(parts[0])
            except ValueError as exc:
                raise error_type("Selic CSV contains an invalid ISO date") from exc
            if observation_date.isoformat() != parts[0] or not _CSV_RATE.fullmatch(parts[1]):
                raise error_type("Selic CSV contains a noncanonical date or decimal value")
            observations.append(Observation(observation_date, parts[1]))
        if not observations:
            raise error_type("Selic CSV contains no observations")
        try:
            values = validate_observations(observations, observations[-1].date, len(observations))
        except SourceError as exc:
            raise error_type(f"Selic CSV observations are invalid: {exc}") from exc
        if csv_bytes(values) != content:
            raise error_type("Selic CSV bytes are not in canonical generated format")
        return values

    @classmethod
    def _validate_manifest_pair(cls, manifest: dict, content: bytes) -> tuple[Observation, ...]:
        cls._validate_manifest(manifest)
        current = manifest["current"]
        if sha256(content) != current["sha256"]:
            raise ManifestError("Selic manifest hash does not match its CSV")
        observations = cls._parse_csv_content(content)
        count = len(observations)
        if count != current["reported_count"] or count != current["observation_count"]:
            raise ManifestError("Selic manifest CSV observation counts do not match the CSV")
        if (
            observations[0].date.isoformat() != current["first_date"]
            or observations[-1].date.isoformat() != current["last_date"]
        ):
            raise ManifestError("Selic manifest date coverage does not match the CSV")
        return observations

    def _verify_backup(self, reference: dict) -> None:
        csv_path = self._resolve_backup(reference["csv_path"])
        manifest_path = self._resolve_backup(reference["manifest_path"])
        try:
            content = csv_path.read_bytes()
            manifest_bytes = manifest_path.read_bytes()
        except OSError as exc:
            raise ManifestError("cannot read referenced Selic backup pair") from exc
        if sha256(content) != reference["csv_sha256"]:
            raise ManifestError(f"referenced Selic CSV backup hash mismatch: {csv_path}")
        if sha256(manifest_bytes) != reference["manifest_sha256"]:
            raise ManifestError(f"referenced Selic manifest backup hash mismatch: {manifest_path}")
        try:
            backup_manifest = json.loads(manifest_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ManifestError("referenced Selic backup manifest is invalid") from exc
        self._validate_manifest_pair(backup_manifest, content)

    def _backup(self, path: Path, content: bytes, kind: str, retrieved_at: str) -> dict:
        digest = sha256(content)
        stamp = retrieved_at.replace("-", "").replace(":", "").replace(".", "")
        target = self.backup_root / f"{stamp}-{digest}-{kind}"
        if target.exists() and sha256(target.read_bytes()) != digest:
            target = self.backup_root / f"{stamp}-{digest}-{uuid.uuid4().hex[:8]}-{kind}"
        if not target.exists():
            _atomic_write(target, content)
        if sha256(target.read_bytes()) != digest:
            raise StoreError(f"backup verification failed: {target}")
        return {"path": target.relative_to(self.data_root).as_posix(), "sha256": digest}

    def _backup_pair(
        self, old_content: bytes | None, old_manifest_bytes: bytes | None, timestamp: str
    ) -> dict | None:
        if old_content is None and old_manifest_bytes is None:
            return None
        if old_content is None or old_manifest_bytes is None:
            raise ManifestError("cannot back up an incomplete Selic CSV/manifest pair")
        csv_backup = self._backup(self.active_path, old_content, "selic_sgs_11.csv", timestamp)
        manifest_backup = self._backup(
            self.manifest_path, old_manifest_bytes, "manifest.json", timestamp
        )
        return {
            "csv_path": csv_backup["path"],
            "csv_sha256": csv_backup["sha256"],
            "manifest_path": manifest_backup["path"],
            "manifest_sha256": manifest_backup["sha256"],
        }

    @staticmethod
    def _append_backup(record: dict, backup: dict | None) -> None:
        references = record.setdefault("previous_versions", [])
        keys = ("csv_path", "csv_sha256", "manifest_path", "manifest_sha256")
        record["previous_versions"] = [
            {key: reference[key] for key in keys} for reference in references
        ]
        if backup is None:
            return
        key = (backup["csv_path"], backup["manifest_path"])
        if not any(
            (item.get("csv_path"), item.get("manifest_path")) == key
            for item in record["previous_versions"]
        ):
            record["previous_versions"].append(
                {field: backup[field] for field in keys}
            )

    def _resolve_backup(self, relative: str) -> Path:
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or len(pure.parts) != 3
            or pure.parts[:2] != ("backups", "selic")
        ):
            raise RestoreError("backup path is outside backups/selic")
        target = (self.data_root / Path(*pure.parts)).resolve()
        if os.path.commonpath((str(self.backup_root.resolve()), str(target))) != str(self.backup_root.resolve()):
            raise RestoreError("backup path escapes backups/selic")
        return target

    def recover(self) -> None:
        if not self.pending_path.exists():
            return
        try:
            pending = json.loads(self.pending_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"cannot read Selic write-ahead record: {exc}") from exc
        if not isinstance(pending, dict):
            raise ManifestError("Selic write-ahead record is not an object")
        old_hash = pending.get("old_csv_sha256")
        new_hash = pending.get("new_csv_sha256")
        old_manifest_hash = pending.get("old_manifest_sha256")
        old_manifest = pending.get("old_manifest")
        new_manifest = pending.get("new_manifest")
        if new_hash is not None and (not isinstance(new_hash, str) or not _HASH.fullmatch(new_hash)):
            raise ManifestError("write-ahead record has an invalid new CSV hash")
        if old_hash is not None and (not isinstance(old_hash, str) or not _HASH.fullmatch(old_hash)):
            raise ManifestError("write-ahead record has an invalid old CSV hash")
        if old_manifest_hash is not None and (
            not isinstance(old_manifest_hash, str) or not _HASH.fullmatch(old_manifest_hash)
        ):
            raise ManifestError("write-ahead record has an invalid old manifest hash")
        self._validate_manifest(new_manifest)
        if new_manifest["current"]["sha256"] != new_hash:
            raise ManifestError("write-ahead record disagrees with its new manifest")
        new_manifest_bytes = self._manifest_bytes(new_manifest)
        new_manifest_hash = sha256(new_manifest_bytes)
        recorded_new_manifest_hash = pending.get("new_manifest_sha256")
        if recorded_new_manifest_hash is not None and recorded_new_manifest_hash != new_manifest_hash:
            raise ManifestError("write-ahead record has an invalid new manifest hash")
        if old_hash is None:
            if old_manifest is not None or old_manifest_hash is not None:
                raise ManifestError("write-ahead record has inconsistent empty prior state")
        else:
            self._validate_manifest(old_manifest)
            if old_manifest["current"]["sha256"] != old_hash or old_manifest_hash is None:
                raise ManifestError("write-ahead record disagrees with its old manifest")
        backup = pending.get("backup")
        rollback_manifest = None
        rollback_manifest_bytes = None
        rollback_manifest_hash = None
        if old_manifest is not None:
            rollback_manifest = deepcopy(old_manifest)
            self._append_backup(rollback_manifest["current"], backup)
            self._validate_manifest(rollback_manifest)
            rollback_manifest_bytes = self._manifest_bytes(rollback_manifest)
            rollback_manifest_hash = sha256(rollback_manifest_bytes)
        if backup is not None:
            self._verify_backup(backup)
        active_content = self.active_path.read_bytes() if self.active_path.exists() else None
        active_hash = sha256(active_content) if active_content is not None else None
        current_manifest_hash = (
            sha256(self.manifest_path.read_bytes()) if self.manifest_path.exists() else None
        )
        if active_hash == new_hash:
            self._validate_manifest_pair(new_manifest, active_content)
        elif active_hash == old_hash and old_manifest is not None:
            self._validate_manifest_pair(old_manifest, active_content)
            if rollback_manifest is not None:
                self._validate_manifest_pair(rollback_manifest, active_content)
        if active_hash == new_hash:
            if current_manifest_hash == new_manifest_hash:
                self.pending_path.unlink()
                return
            if current_manifest_hash == old_manifest_hash:
                _atomic_write(self.manifest_path, new_manifest_bytes)
                self.pending_path.unlink()
                return
            raise ManifestError(
                "active Selic CSV is new but the manifest matches neither known transaction state; "
                "preserved for recovery"
            )
        if active_hash == old_hash:
            if current_manifest_hash == old_manifest_hash:
                if rollback_manifest_bytes is not None and rollback_manifest_hash != old_manifest_hash:
                    _atomic_write(self.manifest_path, rollback_manifest_bytes)
                self.pending_path.unlink()
                return
            if rollback_manifest_hash is not None and current_manifest_hash == rollback_manifest_hash:
                self.pending_path.unlink()
                return
            raise ManifestError(
                "active Selic CSV is old but the manifest matches neither known rollback state; "
                "preserved for recovery"
            )
        raise ManifestError(
            "active Selic CSV matches neither side of the pending update; preserved for recovery"
        )

    def _commit_locked(
        self,
        content: bytes,
        manifest: dict,
        old_manifest: dict | None,
        old_content: bytes | None,
        old_manifest_bytes: bytes | None,
        timestamp: str,
    ) -> dict:
        backup = self._backup_pair(old_content, old_manifest_bytes, timestamp)
        self._append_backup(manifest["current"], backup)
        self._validate_manifest(manifest)
        content_hash = sha256(content)
        manifest_bytes = self._manifest_bytes(manifest)
        pending = {
            "old_csv_sha256": sha256(old_content) if old_content is not None else None,
            "old_manifest_sha256": (
                sha256(old_manifest_bytes) if old_manifest_bytes is not None else None
            ),
            "new_csv_sha256": content_hash,
            "new_manifest_sha256": sha256(manifest_bytes),
            "backup": backup,
            "old_manifest": deepcopy(old_manifest),
            "new_manifest": manifest,
        }
        _atomic_write(
            self.pending_path,
            json.dumps(pending, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        _atomic_write(self.active_path, content)
        _atomic_write(self.manifest_path, manifest_bytes)
        self.pending_path.unlink()
        return {
            "status": "saved" if old_content is None else "updated",
            "sha256": content_hash,
            "path": self.active_path,
        }

    def _save_locked(self, source: SourceResult, now: datetime) -> dict:
        timestamp = utc_timestamp(now)
        observations = validate_observations(
            source.observations, source.latest_date, source.reported_count
        )
        content = csv_bytes(observations)
        new_hash = sha256(content)
        old_manifest = self._read_manifest()
        old_content = self.active_path.read_bytes() if self.active_path.exists() else None
        old_manifest_bytes = self.manifest_path.read_bytes() if self.manifest_path.exists() else None
        if old_content is not None and old_manifest is None:
            raise ManifestError("active Selic CSV has no matching provenance manifest")
        if old_content is None and old_manifest is not None:
            raise ManifestError("Selic manifest exists but its active CSV is missing")
        if old_content is not None:
            self._validate_manifest_pair(old_manifest, old_content)
        if old_content is not None and sha256(old_content) == new_hash:
            if old_manifest["current"]["sha256"] != new_hash:
                raise ManifestError("active Selic CSV hash disagrees with its manifest")
            return {"status": "unchanged", "sha256": new_hash, "path": self.active_path}

        previous_versions = (
            deepcopy(old_manifest["current"].get("previous_versions", []))
            if old_manifest else []
        )
        record = {
            "retrieved_at": timestamp,
            "requested_start": _REQUESTED_START,
            "requested_end": source.latest_date.isoformat(),
            "first_date": observations[0].date.isoformat(),
            "last_date": observations[-1].date.isoformat(),
            "reported_count": source.reported_count,
            "observation_count": len(observations),
            "sha256": new_hash,
            "format": _CSV_FORMAT,
            "previous_versions": previous_versions,
        }
        manifest = {
            "schema_version": 1,
            "source_url": SOURCE_URL,
            "dataset_url": DATASET_URL,
            "series_id": 11,
            "unit": UNIT_FOR_MANIFEST,
            "license_listed_by_bcb": _BCB_LICENSE,
            "current": record,
        }
        return self._commit_locked(
            content, manifest, old_manifest, old_content, old_manifest_bytes, timestamp
        )

    def save_locked(self, source: SourceResult, now: datetime) -> dict:
        self.recover()
        return self._save_locked(source, now)

    def save(self, source: SourceResult, now: datetime) -> dict:
        with self.lock():
            return self.save_locked(source, now)

    def restore(self, backup_path: str, now: datetime) -> dict:
        with self.lock():
            self.recover()
            manifest = self._read_manifest()
            if manifest is None:
                raise RestoreError("no Selic manifest is available")
            active_content = self.active_path.read_bytes() if self.active_path.exists() else None
            if active_content is None:
                raise ManifestError("Selic active CSV is missing before restore")
            self._validate_manifest_pair(manifest, active_content)
            reference = next(
                (item for item in manifest["current"]["previous_versions"]
                 if backup_path in (item["csv_path"], item["manifest_path"])), None
            )
            if reference is None:
                raise RestoreError("backup is not listed in Selic manifest previous_versions")
            self._resolve_backup(backup_path)
            try:
                content = self._resolve_backup(reference["csv_path"]).read_bytes()
                historical_manifest_bytes = self._resolve_backup(reference["manifest_path"]).read_bytes()
            except OSError as exc:
                raise RestoreError(f"cannot read Selic backup: {exc}") from exc
            if sha256(content) != reference["csv_sha256"]:
                raise RestoreError("paired Selic CSV backup hash does not match manifest")
            if sha256(historical_manifest_bytes) != reference["manifest_sha256"]:
                raise RestoreError("paired Selic manifest backup hash does not match manifest")
            try:
                historical_manifest = json.loads(historical_manifest_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RestoreError(f"Selic manifest backup is invalid: {exc}") from exc
            observations = self._validate_manifest_pair(historical_manifest, content)
            record = deepcopy(historical_manifest["current"])

            timestamp = utc_timestamp(now)
            historical_references = deepcopy(record.get("previous_versions", []))
            restored_current = record
            restored_current["previous_versions"] = deepcopy(
                manifest["current"].get("previous_versions", [])
            )
            for item in historical_references:
                self._append_backup(restored_current, item)
            restored_current["restored_at"] = timestamp
            new_manifest = deepcopy(manifest)
            new_manifest["current"] = restored_current
            old_content = active_content
            old_manifest_bytes = self.manifest_path.read_bytes()
            result = self._commit_locked(
                content, new_manifest, manifest, old_content, old_manifest_bytes, timestamp
            )
            return result


UNIT_FOR_MANIFEST = "% p.d."
