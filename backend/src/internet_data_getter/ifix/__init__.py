"""IFIX data acquisition."""
from __future__ import annotations
from pathlib import Path

from .b3_source import B3IfixClient
from .service import IfixAcquisition
from .storage import FileStore


def acquire_ifix(data_dir: Path | str | None = None):
    """Download and safely preserve IFIX files on explicit request."""
    if data_dir is None:
        data_dir = Path(__file__).resolve().parents[4] / "data"
    return IfixAcquisition(B3IfixClient(), FileStore(data_dir)).run()
