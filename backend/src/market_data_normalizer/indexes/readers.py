"""Pandas readers for the source formats used by index normalization."""

from datetime import date
import re
from pathlib import Path

import pandas as pd


MONTHS = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
_B3_HEADER = re.compile(r"^(IBOV|IFIX)\s*-\s*(\d{4})$")
_BR_NUMBER = re.compile(r"(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?$")
_STANDARD_NUMBER = re.compile(r"\d+(?:\.\d+)?$")
_NUMERIC_LABEL = re.compile(r"[+-]?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:[,.]\d+)?$")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")


class NormalizationError(ValueError):
    """Raised when a source file cannot be normalized without guessing."""


def _decimal_text(value: str, path: Path, row: int, field: str, *, brazilian: bool) -> str:
    text = value.strip()
    pattern = _BR_NUMBER if brazilian else _STANDARD_NUMBER
    if not pattern.fullmatch(text):
        raise NormalizationError(f"{path}: invalid {field} at row {row}: {value!r}")
    if brazilian:
        return text.replace(".", "").replace(",", ".")
    return text


def _read_csv(path: Path, **options) -> pd.DataFrame:
    encoding = options.pop("encoding", "utf-8")
    try:
        with pd.io.common.get_handle(path, "r", encoding=encoding, is_text=True) as handles:
            return pd.read_csv(handles.handle, dtype=str, keep_default_na=False, **options)
    except pd.errors.ParserError as error:
        raise NormalizationError(f"{path}: malformed CSV row width or quoting: {error}") from error
    except (OSError, UnicodeError, ValueError) as error:
        raise NormalizationError(f"{path}: unable to read CSV: {error}") from error


def read_b3_index(path: Path, column: str, expected_symbol: str) -> pd.DataFrame:
    """Expand one B3 daily-evolution annual matrix into date/value rows."""
    matrix = _read_csv(
        path,
        sep=";",
        header=None,
        names=list(range(13)),
        encoding="cp1252",
        engine="python",
    )
    if matrix.shape != (35, 13):
        raise NormalizationError(f"{path}: expected a 35-row, 13-column B3 annual matrix, found {matrix.shape}")
    short_rows = matrix.iloc[1:].isna().any(axis=1)
    if short_rows.any():
        row_index = short_rows[short_rows].index[0]
        raise NormalizationError(f"{path}: malformed B3 row {row_index + 1}: expected exactly 13 fields")
    for row_index, row in matrix.iloc[33:35].iterrows():
        summary_label = row.iat[0].strip()
        if not summary_label or _NUMERIC_LABEL.fullmatch(summary_label):
            raise NormalizationError(
                f"{path}: malformed B3 summary row {row_index + 1}: expected a nonnumeric label"
            )

    header_match = _B3_HEADER.fullmatch(matrix.iat[0, 0].strip())
    if header_match is None or header_match.group(1) != expected_symbol:
        raise NormalizationError(f"{path}: expected {expected_symbol} index header with a year")
    year = int(header_match.group(2))
    month_header = tuple(value.strip() for value in matrix.iloc[1, 1:])
    if matrix.iat[1, 0].strip() != "Dia" or month_header != MONTHS:
        raise NormalizationError(f"{path}: invalid B3 day/month header")

    observations = []
    for expected_day, row_number in enumerate(range(2, 33), start=1):
        row = matrix.iloc[row_number]
        if row.iat[0].strip() != str(expected_day):
            raise NormalizationError(f"{path}: expected day {expected_day} at matrix row {row_number + 1}")
        for month_number, source_value in enumerate(row.iloc[1:], start=1):
            value = source_value.strip()
            if not value:
                continue
            try:
                observation_date = date(year, month_number, expected_day).isoformat()
            except ValueError as error:
                raise NormalizationError(
                    f"{path}: value for invalid date {year:04d}-{month_number:02d}-{expected_day:02d}"
                ) from error
            normalized = _decimal_text(value, path, row_number + 1, expected_symbol, brazilian=True)
            observations.append((observation_date, normalized))

    if not observations:
        raise NormalizationError(f"{path}: no {expected_symbol} observations")
    return pd.DataFrame(observations, columns=["date", column])


def read_daily_series(path: Path, column: str, source_column: str) -> pd.DataFrame:
    """Read the canonical date/value CSV written by the Selic or Yahoo getter."""
    frame = _read_csv(path, engine="python")
    expected_columns = ["date", source_column]
    if not isinstance(frame.index, pd.RangeIndex):
        raise NormalizationError(f"{path}: malformed CSV row width; expected exactly two columns")
    if list(frame.columns) != expected_columns:
        raise NormalizationError(f"{path}: expected columns {expected_columns}, found {list(frame.columns)}")
    if frame.empty:
        raise NormalizationError(f"{path}: no observations")

    observations = []
    for row_number, row in frame.iterrows():
        text_date = row["date"].strip()
        if not _ISO_DATE.fullmatch(text_date):
            raise NormalizationError(f"{path}: invalid ISO date at row {row_number + 2}: {text_date!r}")
        try:
            parsed_date = date.fromisoformat(text_date)
        except ValueError as error:
            raise NormalizationError(f"{path}: invalid date at row {row_number + 2}: {text_date!r}") from error
        if parsed_date.isoformat() != text_date:
            raise NormalizationError(f"{path}: noncanonical date at row {row_number + 2}: {text_date!r}")
        value = _decimal_text(row[source_column], path, row_number + 2, source_column, brazilian=False)
        observations.append((text_date, value))

    return pd.DataFrame(observations, columns=["date", column])
