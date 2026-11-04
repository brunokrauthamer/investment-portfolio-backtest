"""IBOVESPA data acquisition."""
from __future__ import annotations

from pathlib import Path

from .b3_source import B3IbovespaClient
from .service import IbovespaAcquisition
from .storage import FileStore


def acquire_ibovespa(data_dir: Path | str | None = None):
    """Download and safely preserve IBOVESPA files on explicit request."""
    if data_dir is None:
        data_dir = Path(__file__).resolve().parents[4] / "data"
    return IbovespaAcquisition(B3IbovespaClient(), FileStore(data_dir)).run()
