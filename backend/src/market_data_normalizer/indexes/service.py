"""Public service to gather the project's index source CSV files."""

import os
from pathlib import Path
import tempfile

import pandas as pd

from .readers import NormalizationError, read_b3_index, read_daily_series


ASSETS = (
    ("ibovespa", "ibovespa", "b3", "IBOV"),
    ("ifix", "ifix", "b3", "IFIX"),
    ("selic", "selic", "daily", "rate_percent_per_day"),
    ("sp500", "sp500", "daily", "adjusted_close"),
)
OUTPUT_COLUMNS = ("date", "ibovespa", "ifix", "selic", "sp500")
_REPOSITORY_DATA = Path(__file__).resolve().parents[4] / "data"


def _load_asset(data_dir: Path, asset: str, column: str, source_type: str, source_identifier: str) -> pd.DataFrame:
    source_dir = data_dir / asset / "source"
    paths = sorted(path for path in source_dir.glob("*.csv") if path.is_file())
    if not paths:
        raise NormalizationError(f"{source_dir}: no CSV source files for {asset}")

    frames = []
    for path in paths:
        if source_type == "b3":
            frame = read_b3_index(path, column, source_identifier)
        else:
            frame = read_daily_series(path, column, source_identifier)
        duplicate_dates = frame.loc[frame["date"].duplicated(keep=False), "date"].unique().tolist()
        if duplicate_dates:
            raise NormalizationError(f"{path}: duplicate {asset} dates: {duplicate_dates}")
        frames.append(frame)

    combined = pd.concat(frames, ignore_index=True)
    duplicate_dates = combined.loc[combined["date"].duplicated(keep=False), "date"].unique().tolist()
    if duplicate_dates:
        raise NormalizationError(f"{source_dir}: duplicate {asset} dates across source files: {duplicate_dates}")
    return combined.set_index("date")[[column]]


def gather_index_data(data_dir=None) -> Path:
    """Combine the four local index datasets into ``normalized/gathered_data.csv``.

    ``data_dir`` names the root containing the per-asset directories. When
    omitted, the repository's ``data`` directory is used regardless of the
    current working directory. Missing observations remain blank in the
    outer-joined result.
    """
    root = Path(data_dir).expanduser().resolve() if data_dir is not None else _REPOSITORY_DATA
    asset_frames = [
        _load_asset(root, *asset_configuration)
        for asset_configuration in ASSETS
    ]
    gathered = pd.concat(asset_frames, axis=1, join="outer").sort_index(kind="mergesort")
    gathered.index.name = "date"
    gathered = gathered.reset_index().reindex(columns=OUTPUT_COLUMNS)
    output_path = root / "normalized" / "gathered_data.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent,
            prefix=".gathered_data.",
            suffix=".csv",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        gathered.to_csv(temporary_path, index=False, columns=OUTPUT_COLUMNS, na_rep="", encoding="utf-8")
        os.replace(temporary_path, output_path)
    except OSError as error:
        raise NormalizationError(f"{output_path}: unable to publish gathered data: {error}") from error
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return output_path


__all__ = ["NormalizationError", "gather_index_data"]
