"""IFIX configuration for shared B3 annual-file storage."""

from __future__ import annotations

from pathlib import Path

from backend.src.internet_data_getter.b3_storage import (
    B3FileStore, LockError, ManifestError, SaveResult, _atomic_write, _sha256,
)
from .b3_source import PAGE_URL, SOURCE_FILENAME, validate_csv


class FileStore(B3FileStore):
    asset_key = "ifix"
    display_name = "IFIX"
    filename_prefix = "IFIX"
    source_filename = SOURCE_FILENAME
    page_url = PAGE_URL
    validator = staticmethod(validate_csv)

    def _atomic_write(self, path: Path, content: bytes) -> None:
        _atomic_write(path, content)
