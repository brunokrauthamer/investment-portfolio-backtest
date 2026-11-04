"""Build a daily returns CSV from the normalized local market data."""

from __future__ import annotations

from datetime import date, datetime
import math
import os
from pathlib import Path
import re
import tempfile

import pandas as pd


OUTPUT_COLUMNS = ("date", "ibovespa", "ifix", "selic", "sp500")
GATHERED_COLUMNS = OUTPUT_COLUMNS
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
_REPOSITORY_DATA = Path(__file__).resolve().parents[4] / "data"


class NormalizationError(ValueError):
    """Raised when local market data cannot be converted without guessing."""


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        if b"\x00" in path.read_bytes():
            raise NormalizationError(f"{path}: malformed CSV contains a NUL byte")
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", engine="python")
    except NormalizationError:
        raise
    except pd.errors.ParserError as error:
        raise NormalizationError(f"{path}: malformed CSV row width or quoting: {error}") from error
    except (OSError, UnicodeError, ValueError) as error:
        raise NormalizationError(f"{path}: unable to read CSV: {error}") from error

    if not isinstance(frame.index, pd.RangeIndex):
        raise NormalizationError(f"{path}: malformed CSV row width")
    if frame.empty:
        raise NormalizationError(f"{path}: no observations")
    return frame


def _parse_iso_date(text: str, path: Path, row_number: int) -> date:
    value = text.strip()
    if not _ISO_DATE.fullmatch(value):
        raise NormalizationError(f"{path}: invalid ISO date at row {row_number}: {text!r}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise NormalizationError(f"{path}: invalid date at row {row_number}: {text!r}") from error
    if parsed.isoformat() != value:
        raise NormalizationError(f"{path}: noncanonical date at row {row_number}: {text!r}")
    return parsed


def _required_cell(text: str | None, path: Path, row_number: int, field: str) -> str:
    if text is None:
        raise NormalizationError(
            f"{path}: malformed CSV row at row {row_number}: missing field {field!r}"
        )
    return text


def _parse_number(text: str | None, path: Path, row_number: int, field: str, *, positive: bool) -> float | None:
    text = _required_cell(text, path, row_number, field)
    value = text.strip()
    if not value:
        return None
    if not _NUMBER.fullmatch(value):
        raise NormalizationError(f"{path}: invalid {field} at row {row_number}: {text!r}")
    number = float(value)
    if not math.isfinite(number):
        raise NormalizationError(f"{path}: non-finite {field} at row {row_number}: {text!r}")
    if positive and number <= 0:
        raise NormalizationError(f"{path}: {field} must be positive at row {row_number}: {text!r}")
    return number


def _read_gathered(path: Path) -> list[dict[str, float | date | None]]:
    frame = _read_csv(path)
    if list(frame.columns) != list(GATHERED_COLUMNS):
        raise NormalizationError(f"{path}: expected columns {list(GATHERED_COLUMNS)}, found {list(frame.columns)}")

    observations: list[dict[str, float | date | None]] = []
    seen_dates = set()
    previous_date = None
    for index, row in frame.iterrows():
        row_number = index + 2
        observation_date = _parse_iso_date(row["date"], path, row_number)
        if observation_date in seen_dates:
            raise NormalizationError(f"{path}: duplicate gathered date {observation_date.isoformat()}")
        if previous_date is not None and observation_date <= previous_date:
            raise NormalizationError(f"{path}: gathered dates must be in strictly ascending order")
        seen_dates.add(observation_date)
        previous_date = observation_date
        observation: dict[str, float | date | None] = {"date": observation_date}
        for column in OUTPUT_COLUMNS[1:]:
            observation[column] = _parse_number(
                row[column], path, row_number, column, positive=column != "selic"
            )
        observations.append(observation)
    return observations


def _read_currency(data_dir: Path) -> dict[date, float]:
    source_dir = data_dir / "dolar" / "source"
    paths = sorted(path for path in source_dir.glob("*.csv") if path.is_file())
    if not paths:
        raise NormalizationError(f"{source_dir}: no CSV source files for currency")

    observations: dict[date, float] = {}
    for path in paths:
        frame = _read_csv(path)
        if list(frame.columns) != ["Data", "price"]:
            raise NormalizationError(f"{path}: expected columns ['Data', 'price'], found {list(frame.columns)}")
        for index, row in frame.iterrows():
            row_number = index + 2
            text_date = _required_cell(row["Data"], path, row_number, "Data").strip()
            try:
                observation_date = datetime.strptime(text_date, "%d.%m.%Y").date()
            except ValueError as error:
                raise NormalizationError(f"{path}: invalid currency date at row {row_number}: {text_date!r}") from error
            if observation_date.strftime("%d.%m.%Y") != text_date:
                raise NormalizationError(f"{path}: noncanonical currency date at row {row_number}: {text_date!r}")
            if observation_date in observations:
                raise NormalizationError(f"{source_dir}: duplicate currency dates: {observation_date.isoformat()}")
            price_text = _required_cell(row["price"], path, row_number, "price")
            price = _parse_number(price_text.replace(",", "."), path, row_number, "price", positive=True)
            if price is None:
                raise NormalizationError(f"{path}: missing price at row {row_number}")
            observations[observation_date] = price
    return observations


def _asof_currency(dates: list[date], observations: dict[date, float]) -> list[float | None]:
    available = sorted(observations.items())
    currency_index = 0
    last_price = None
    prices = []
    for observation_date in dates:
        while currency_index < len(available) and available[currency_index][0] <= observation_date:
            last_price = available[currency_index][1]
            currency_index += 1
        prices.append(last_price)
    return prices


def _ratio_return(current: float, previous: float, field: str, observation_date: date) -> float:
    result = current / previous - 1
    if not math.isfinite(result):
        raise NormalizationError(f"{field}: non-finite return on {observation_date.isoformat()}")
    return result


def _calculate_returns(
    observations: list[dict[str, float | date | None]], currency_prices: list[float | None]
) -> pd.DataFrame:
    result_rows = []
    previous_levels: dict[str, float | None] = {"ibovespa": None, "ifix": None}
    previous_sp500: float | None = None
    previous_sp500_currency: float | None = None

    for index, observation in enumerate(observations):
        observation_date = observation["date"]
        assert isinstance(observation_date, date)
        output_row: dict[str, float | str] = {"date": observation_date.isoformat()}

        for asset in ("ibovespa", "ifix"):
            current_level = observation[asset]
            if current_level is None:
                output_row[asset] = 0.0
                continue
            if index and previous_levels[asset] is not None:
                output_row[asset] = _ratio_return(current_level, previous_levels[asset], asset, observation_date)
            else:
                output_row[asset] = 0.0
            previous_levels[asset] = current_level

        selic = observation["selic"]
        output_row["selic"] = selic / 100 if selic is not None else 0.0

        current_sp500 = observation["sp500"]
        current_currency = currency_prices[index]
        sp500_return = 0.0
        if current_sp500 is not None:
            if (index and previous_sp500 is not None and previous_sp500_currency is not None
                    and current_currency is not None):
                index_return = _ratio_return(current_sp500, previous_sp500, "sp500", observation_date)
                currency_return = _ratio_return(current_currency, previous_sp500_currency, "currency", observation_date)
                sp500_return = (1 + index_return) * (1 + currency_return) - 1
                if not math.isfinite(sp500_return):
                    raise NormalizationError(f"sp500: non-finite return on {observation_date.isoformat()}")
            previous_sp500 = current_sp500
            previous_sp500_currency = current_currency
        output_row["sp500"] = sp500_return

        if index:
            result_rows.append(output_row)

    return pd.DataFrame(result_rows, columns=OUTPUT_COLUMNS)


def generate_daily_returns_reais(data_dir=None) -> Path:
    """Write daily returns to ``normalized/daily_returns_reais.csv``.

    The input root contains ``normalized/gathered_data.csv`` and the direct
    currency source CSV files under ``dolar/source``. The first gathered row
    supplies history but does not appear in the output.
    """
    root = Path(data_dir).expanduser().resolve() if data_dir is not None else _REPOSITORY_DATA
    gathered_path = root / "normalized" / "gathered_data.csv"
    gathered = _read_gathered(gathered_path)
    currency = _read_currency(root)
    dates = [row["date"] for row in gathered]
    currency_prices = _asof_currency(dates, currency)
    returns = _calculate_returns(gathered, currency_prices)

    output_path = root / "normalized" / "daily_returns_reais.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent,
            prefix=".daily_returns_reais.",
            suffix=".csv",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        returns.to_csv(temporary_path, index=False, columns=OUTPUT_COLUMNS, encoding="utf-8")
        os.replace(temporary_path, output_path)
    except (OSError, ValueError) as error:
        raise NormalizationError(f"{output_path}: unable to publish daily returns: {error}") from error
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return output_path


__all__ = ["NormalizationError", "generate_daily_returns_reais"]
