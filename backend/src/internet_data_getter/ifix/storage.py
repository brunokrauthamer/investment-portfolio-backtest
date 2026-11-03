"""Safe local storage for original IFIX source files and their history."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Iterator
import uuid

from backend.src.internet_data_getter.ifix.b3_source import PAGE_URL, SOURCE_FILENAME, validate_csv


_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class LockError(RuntimeError):
    """Another acquisition or restore owns the IFIX destination."""


class ManifestError(OSError):
    """Stored provenance is invalid or cannot be safely recovered."""


@dataclass(frozen=True)
class SaveResult:
    year: int
    status: str
    sha256: str
    path: Path
    backup: Path | None = None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_timestamp(now: datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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


class FileStore:
    """Store active files, a validated manifest, write-ahead recovery and backups."""

    def __init__(self, data_root: Path | str):
        self.data_root = Path(data_root)
        self.ifix_root = self.data_root / "ifix"
        self.active_root = self.ifix_root / "source"
        self.backup_root = self.data_root / "backups" / "ifix"
        self.manifest_path = self.ifix_root / "manifest.json"
        self.lock_path = self.ifix_root / ".acquisition.lock"

    @contextlib.contextmanager
    def lock(self) -> Iterator[None]:
        self.ifix_root.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise LockError(
                f"another operation is running (or a stale lock remains at {self.lock_path}); "
                "confirm no operation is active before removing a stale lock"
            ) from exc
        try:
            lock_content = f"pid={os.getpid()}\ncreated_at={_utc_timestamp(datetime.now(timezone.utc))}\n".encode()
            os.write(fd, lock_content)
            os.fsync(fd)
            yield
        finally:
            os.close(fd)
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass

    def _record_metadata(self, year: int, record, *, current: bool) -> None:
        where = f"manifest record for {year}"
        if not isinstance(record, dict):
            raise ManifestError(f"{where} must be an object")
        if record.get("period") != str(year):
            raise ManifestError(f"{where} has an invalid period")
        if record.get("filename") != f"IFIX_{year}_Evolucao_Diaria.csv":
            raise ManifestError(f"{where} has an invalid active filename")
        if record.get("source_filename") != SOURCE_FILENAME:
            raise ManifestError(f"{where} has an invalid source filename")
        if not isinstance(record.get("source_url"), str) or not record["source_url"].startswith("https://"):
            raise ManifestError(f"{where} has an invalid source URL")
        retrieved = record.get("retrieved_at")
        if retrieved is not None and not isinstance(retrieved, str):
            raise ManifestError(f"{where} has an invalid retrieval time")
        if not isinstance(record.get("sha256"), str) or not _DIGEST.fullmatch(record["sha256"]):
            raise ManifestError(f"{where} has an invalid content hash")
        if current and not isinstance(record.get("previous_versions"), list):
            raise ManifestError(f"{where} previous_versions must be a list")
        if "restored_from" in record:
            self._backup_path(year, record["restored_from"])
        if "restored_at" in record and not isinstance(record["restored_at"], str):
            raise ManifestError(f"{where} has an invalid restore time")

    def _backup_path(self, year: int, relative_path) -> Path:
        if not isinstance(relative_path, str) or "\\" in relative_path:
            raise ManifestError(f"manifest backup path for {year} is invalid")
        pure = PurePosixPath(relative_path)
        if (
            pure.is_absolute()
            or len(pure.parts) != 4
            or pure.parts[:3] != ("backups", "ifix", str(year))
            or pure.name in ("", ".", "..")
            or pure.suffix.lower() != ".csv"
        ):
            raise ManifestError(f"manifest backup path for {year} is invalid")
        target = self.data_root.joinpath(*pure.parts).resolve()
        scope = (self.backup_root / str(year)).resolve()
        if os.path.commonpath((str(scope), str(target))) != str(scope):
            raise ManifestError(f"manifest backup path for {year} escapes its backup directory")
        return target

    def _backup_reference(self, year: int, reference) -> None:
        if not isinstance(reference, dict):
            raise ManifestError(f"manifest backup reference for {year} must be an object")
        self._backup_path(year, reference.get("path"))
        if not isinstance(reference.get("sha256"), str) or not _DIGEST.fullmatch(reference["sha256"]):
            raise ManifestError(f"manifest backup reference for {year} has an invalid hash")
        historical = reference.get("record")
        if historical is not None:
            self._record_metadata(year, historical, current=False)
            if historical["sha256"] != reference["sha256"]:
                raise ManifestError(f"manifest backup reference for {year} disagrees with its record")

    def _validate_manifest(self, manifest) -> None:
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
            raise ManifestError(f"manifest has an unsupported format: {self.manifest_path}")
        if not isinstance(manifest.get("source"), str) or not manifest["source"].startswith("https://"):
            raise ManifestError(f"manifest has an invalid source: {self.manifest_path}")
        files = manifest.get("files")
        if not isinstance(files, dict):
            raise ManifestError(f"manifest files must be an object: {self.manifest_path}")
        for key, record in files.items():
            if not isinstance(key, str) or not key.isdigit() or int(key) < 2011:
                raise ManifestError(f"manifest contains an invalid IFIX period: {key!r}")
            year = int(key)
            self._record_metadata(year, record, current=True)
            for reference in record["previous_versions"]:
                self._backup_reference(year, reference)

        pending = manifest.get("pending_updates", {})
        if not isinstance(pending, dict):
            raise ManifestError("manifest pending_updates must be an object")
        for key, update in pending.items():
            if not isinstance(key, str) or not key.isdigit() or int(key) < 2011 or not isinstance(update, dict):
                raise ManifestError(f"manifest has an invalid pending update: {key!r}")
            year = int(key)
            self._record_metadata(year, update.get("new_record"), current=True)
            old_hash = update.get("old_sha256")
            if old_hash is not None and (not isinstance(old_hash, str) or not _DIGEST.fullmatch(old_hash)):
                raise ManifestError(f"manifest pending update for {year} has an invalid old hash")
            backup = update.get("backup")
            if backup is not None:
                self._backup_reference(year, backup)
            old_record = update.get("old_record")
            if old_record is not None:
                self._record_metadata(year, old_record, current=False)

    def _manifest_bytes(self, manifest: dict) -> bytes:
        return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

    def _write_manifest(self, manifest: dict) -> None:
        _atomic_write(self.manifest_path, self._manifest_bytes(manifest))

    def _read_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"schema_version": 1, "source": PAGE_URL, "files": {}, "pending_updates": {}}
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"cannot safely read manifest {self.manifest_path}: {exc}") from exc
        self._validate_manifest(manifest)
        manifest.setdefault("pending_updates", {})
        if manifest["pending_updates"]:
            self._recover_pending(manifest)
        return manifest

    def _relative_backup(self, year: int, reference: dict) -> tuple[Path, bytes]:
        path = self._backup_path(year, reference["path"])
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise ManifestError(f"cannot read backup for {year}: {path}: {exc}") from exc
        if _sha256(content) != reference["sha256"]:
            raise ManifestError(f"backup hash does not match the manifest for {year}: {path}")
        return path, content

    def _write_backup(self, year: int, previous: bytes, now: datetime, previous_record) -> dict:
        digest = _sha256(previous)
        timestamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        backup = self.backup_root / str(year) / f"{timestamp}-{digest}-{uuid.uuid4().hex[:8]}-{year}.csv"
        _atomic_write(backup, previous)
        if _sha256(backup.read_bytes()) != digest:
            raise OSError(f"backup verification failed: {backup}")
        historical = self._historical_record(year, digest, previous_record)
        return {
            "path": backup.relative_to(self.data_root).as_posix(),
            "sha256": digest,
            "record": historical,
        }

    @staticmethod
    def _historical_record(year: int, digest: str, previous_record) -> dict:
        if isinstance(previous_record, dict) and previous_record.get("sha256") == digest:
            return {key: value for key, value in previous_record.items() if key != "previous_versions"}
        return {
            "period": str(year),
            "filename": f"IFIX_{year}_Evolucao_Diaria.csv",
            "source_filename": SOURCE_FILENAME,
            "source_url": PAGE_URL,
            "retrieved_at": None,
            "sha256": digest,
        }

    def _file_record(self, year: int, digest: str, retrieved_at: str, versions: list, **extra) -> dict:
        record = {
            "period": str(year),
            "filename": f"IFIX_{year}_Evolucao_Diaria.csv",
            "source_filename": SOURCE_FILENAME,
            "source_url": PAGE_URL,
            "retrieved_at": retrieved_at,
            "sha256": digest,
            "previous_versions": versions,
        }
        record.update(extra)
        return record

    def _pending_update(self, manifest: dict, year: int, active: Path, new_record: dict, backup) -> dict:
        old_hash = _sha256(active.read_bytes()) if active.exists() else None
        existing_record = manifest["files"].get(str(year))
        old_record = None
        if old_hash is not None:
            old_record = self._historical_record(year, old_hash, existing_record)
            old_record["previous_versions"] = list((existing_record or {}).get("previous_versions", []))
            if backup is not None and not any(
                reference["path"] == backup["path"] for reference in old_record["previous_versions"]
            ):
                old_record["previous_versions"].append(backup)
        update = {
            "old_sha256": old_hash,
            "old_record": old_record,
            "backup": backup,
            "new_record": new_record,
        }
        manifest["pending_updates"][str(year)] = update
        self._validate_manifest(manifest)
        self._write_manifest(manifest)
        return update

    def _recover_pending(self, manifest: dict) -> None:
        for key, update in list(manifest["pending_updates"].items()):
            year = int(key)
            new_record = update["new_record"]
            active = self.active_root / new_record["filename"]
            active_hash = _sha256(active.read_bytes()) if active.exists() else None
            if active_hash == new_record["sha256"]:
                if update.get("backup") is not None:
                    self._relative_backup(year, update["backup"])
                manifest["files"][key] = new_record
            elif active_hash == update.get("old_sha256"):
                old_record = update.get("old_record")
                backup = update.get("backup")
                if backup is not None:
                    self._relative_backup(year, backup)
                    versions = list((old_record or {}).get("previous_versions", []))
                    if not any(item.get("path") == backup["path"] for item in versions):
                        versions.append(backup)
                    if old_record is not None:
                        old_record = dict(old_record)
                        old_record["previous_versions"] = versions
                        manifest["files"][key] = old_record
            else:
                raise ManifestError(
                    f"cannot recover interrupted update for {year}: active file matches neither old nor new hash"
                )
            del manifest["pending_updates"][key]
        self._validate_manifest(manifest)
        self._write_manifest(manifest)

    def _commit(self, manifest: dict, year: int, active: Path, data: bytes, new_record: dict, backup) -> None:
        self._pending_update(manifest, year, active, new_record, backup)
        _atomic_write(active, data)
        manifest["files"][str(year)] = new_record
        del manifest["pending_updates"][str(year)]
        self._validate_manifest(manifest)
        self._write_manifest(manifest)

    def save(self, year: int, content: bytes, now: datetime) -> SaveResult:
        if year < 2011:
            raise ValueError("IFIX acquisition starts in 2011")
        validate_csv(content, year)
        retrieved_at = _utc_timestamp(now)
        digest = _sha256(content)
        active = self.active_root / f"IFIX_{year}_Evolucao_Diaria.csv"
        manifest = self._read_manifest()
        previous_record = manifest["files"].get(str(year))
        versions = list((previous_record or {}).get("previous_versions", []))
        current = active.read_bytes() if active.exists() else None
        backup = None
        status = "saved"
        if current is not None and _sha256(current) == digest:
            status = "unchanged"
        elif current is not None:
            backup = self._write_backup(year, current, now, previous_record)
            versions.append(backup)
            status = "updated"

        new_record = self._file_record(year, digest, retrieved_at, versions)
        if status == "unchanged":
            manifest["files"][str(year)] = new_record
            self._validate_manifest(manifest)
            self._write_manifest(manifest)
        else:
            self._commit(manifest, year, active, content, new_record, backup)
        return SaveResult(year=year, status=status, sha256=digest, path=active, backup=self._backup_path(year, backup["path"]) if backup else None)

    def restore(self, year: int, backup_path: str, now: datetime) -> SaveResult:
        if year < 2011:
            raise ValueError("IFIX acquisition starts in 2011")
        restored_at = _utc_timestamp(now)
        manifest = self._read_manifest()
        current_record = manifest["files"].get(str(year))
        if current_record is None:
            raise ManifestError(f"no manifest history exists for IFIX {year}")
        selected = next(
            (item for item in current_record["previous_versions"] if item["path"] == backup_path), None
        )
        if selected is None:
            raise ManifestError(f"backup is not listed in the manifest for IFIX {year}: {backup_path}")
        selected_path, content = self._relative_backup(year, selected)
        validate_csv(content, year)
        digest = _sha256(content)
        active = self.active_root / f"IFIX_{year}_Evolucao_Diaria.csv"
        current = active.read_bytes() if active.exists() else None
        displaced_backup = None
        versions = list(current_record["previous_versions"])
        if current is not None and _sha256(current) != digest:
            displaced_backup = self._write_backup(year, current, now, current_record)
            versions.append(displaced_backup)
        historical = selected.get("record") or self._historical_record(year, digest, None)
        restored_record = dict(historical)
        restored_record["previous_versions"] = versions
        restored_record["restored_from"] = selected["path"]
        restored_record["restored_at"] = restored_at

        if current is not None and _sha256(current) == digest:
            manifest["files"][str(year)] = restored_record
            self._validate_manifest(manifest)
            self._write_manifest(manifest)
        else:
            self._commit(manifest, year, active, content, restored_record, displaced_backup)
        return SaveResult(year, "restored", digest, active, self._backup_path(year, displaced_backup["path"]) if displaced_backup else None)
