"""Read and validate normalized daily returns for portfolio requests."""

from dataclasses import dataclass
from datetime import date
import math
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError, ParserError


INDEX_COLUMNS = ("ibovespa", "ifix", "selic", "sp500")
EXPECTED_COLUMNS = ("date", *INDEX_COLUMNS)
_DATA_PATH = Path(__file__).resolve().parents[4] / "data" / "normalized" / "daily_returns_reais.csv"


class PortfolioDataError(ValueError):
    """Raised when normalized historical returns cannot support a calculation."""


@dataclass(frozen=True)
class DailyReturnObservation:
    """One available date and its decimal daily asset returns."""

    date: date
    returns: dict[str, float]


def load_daily_returns(
    initial_date: date,
    end_date: date,
    data_path: Path | str | None = None,
) -> list[DailyReturnObservation]:
    """Read the source CSV, validate its complete table, and filter inclusively."""
    path = Path(data_path) if data_path is not None else _DATA_PATH
    try:
        table = pd.read_csv(path, dtype={"date": "string"})
    except (OSError, EmptyDataError, ParserError, UnicodeError, ValueError) as error:
        raise PortfolioDataError("Historical returns are unavailable or invalid.") from error

    if tuple(table.columns) != EXPECTED_COLUMNS:
        raise PortfolioDataError("Historical returns are unavailable or invalid.")

    date_values = table["date"]
    if date_values.isna().any() or not date_values.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        raise PortfolioDataError("Historical returns are unavailable or invalid.")
    try:
        parsed_dates = [date.fromisoformat(value) for value in date_values]
    except ValueError as error:
        raise PortfolioDataError("Historical returns are unavailable or invalid.") from error

    if any(later <= earlier for earlier, later in zip(parsed_dates, parsed_dates[1:])):
        raise PortfolioDataError("Historical returns are unavailable or invalid.")

    date_mask = table["date"].ge(initial_date.isoformat()) & table["date"].le(end_date.isoformat())
    selected = table.loc[date_mask]
    selected_dates = [parsed_dates[index] for index in selected.index]

    return_values: dict[str, list[float]] = {}
    try:
        for column in INDEX_COLUMNS:
            values = pd.to_numeric(selected[column], errors="raise").tolist()
            numeric_values = [float(value) for value in values]
            if any(not math.isfinite(value) or value < -1.0 for value in numeric_values):
                raise PortfolioDataError("Historical returns are unavailable or invalid.")
            return_values[column] = numeric_values
    except (ValueError, TypeError, OverflowError) as error:
        raise PortfolioDataError("Historical returns are unavailable or invalid.") from error

    return [
        DailyReturnObservation(
            date=observation_date,
            returns={column: return_values[column][index] for column in INDEX_COLUMNS},
        )
        for index, observation_date in enumerate(selected_dates)
    ]
