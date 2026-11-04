"""Acquisition of BCB SGS Selic series 11."""
from __future__ import annotations
from pathlib import Path

from .service import SelicAcquisition
from .source import SgsSelicClient
from .storage import SelicFileStore


def acquire_selic(data_dir: Path | str | None = None):
    """Fetch and safely preserve Selic observations after explicit invocation."""
    if data_dir is None:
        data_dir = Path(__file__).resolve().parents[4] / "data"
    return SelicAcquisition(SgsSelicClient(), SelicFileStore(data_dir)).run()
