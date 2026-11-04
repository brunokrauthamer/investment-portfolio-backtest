"""Yahoo Finance S&P 500 source acquisition."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .service import AcquisitionReport, Sp500Acquisition
from .source import YahooFinanceClient
from .storage import Sp500FileStore

def acquire_sp500(
    data_dir: Path | str | None = None,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
) -> AcquisitionReport:
    """Fetch and safely preserve Yahoo's adjusted-close observations explicitly."""
    if data_dir is None:
        data_dir = Path(__file__).resolve().parents[4] / "data"
    return Sp500Acquisition(YahooFinanceClient(), Sp500FileStore(data_dir)).run(
        start_date=start_date, end_date=end_date
    )


__all__ = ["AcquisitionReport", "Sp500Acquisition", "acquire_sp500"]
