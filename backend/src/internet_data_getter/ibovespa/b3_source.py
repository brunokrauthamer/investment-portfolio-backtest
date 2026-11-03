"""B3 IBOV daily-evolution source client."""

from __future__ import annotations

import base64
import csv
import io
import json
import time
import urllib.request
from typing import Callable


PAGE_URL = (
    "https://sistemaswebb3-listados.b3.com.br/"
    "indexStatisticsPage/daily-evolution/IBOV?language=pt-br"
)
DOWNLOAD_ENDPOINT = (
    "https://sistemaswebb3-listados.b3.com.br/"
    "indexStatisticsProxy/IndexCall/GetDownloadPortfolioDay/"
)
MONTH_HEADERS = ["Dia", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
SOURCE_FILENAME = "Evolucao_Diaria.csv"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_PACING_SECONDS = 0.2


class DownloadError(RuntimeError):
    """A source response did not contain the expected annual CSV."""


def available_years(current_year: int) -> list[int]:
    """Return annual page options from 2011 through the current year."""
    if current_year < 2011:
        return []
    return list(range(2011, current_year + 1))


def _download_url(year: int) -> str:
    payload = json.dumps(
        {"index": "IBOV", "language": "pt-br", "year": str(year)},
        separators=(",", ":"),
    ).encode("utf-8")
    return DOWNLOAD_ENDPOINT + base64.b64encode(payload).decode("ascii")


def validate_csv(content: bytes, year: int) -> None:
    """Reject truncated/wrong-period exports while allowing future months to be blank."""
    try:
        rows = [
            row
            for row in csv.reader(io.StringIO(content.decode("cp1252")), delimiter=";", strict=True)
            if row
        ]
    except (UnicodeDecodeError, csv.Error) as exc:
        raise DownloadError(f"year {year}: response is not a readable B3 CSV") from exc

    if len(rows) != 35 or rows[0] != [f"IBOV - {year}"] or rows[1] != MONTH_HEADERS:
        raise DownloadError(f"year {year}: response has an unexpected or incomplete IBOV CSV header")

    day_rows = rows[2:33]
    if any(
        len(row) != 13 or row[0] != str(day)
        for day, row in enumerate(day_rows, start=1)
    ):
        raise DownloadError(f"year {year}: response has a truncated or malformed day matrix")

    summary_rows = rows[33:]
    if any(len(row) != 13 or not row[0].strip() or row[0].isdigit() for row in summary_rows):
        raise DownloadError(f"year {year}: response has an incomplete summary section")

    if not any(cell.strip() for row in day_rows for cell in row[1:]):
        raise DownloadError(f"year {year}: CSV contains no daily observations")


class B3IbovespaClient:
    """Fetch annual downloads through the same endpoint used by B3's page."""

    def __init__(
        self,
        opener: Callable = urllib.request.urlopen,
        sleeper: Callable[[float], None] = time.sleep,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        pacing_seconds: float = DEFAULT_PACING_SECONDS,
    ):
        self._opener = opener
        self._sleep = sleeper
        self._timeout = timeout
        self._pacing_seconds = pacing_seconds

    def download_year(self, year: int) -> bytes:
        if year < 2011:
            raise ValueError("IBOV acquisition starts in 2011")
        if self._pacing_seconds:
            self._sleep(self._pacing_seconds)
        try:
            with self._opener(_download_url(year), timeout=self._timeout) as response:
                if response.status != 200:
                    raise DownloadError(f"year {year}: B3 returned HTTP {response.status}")
                encoded = response.read()
        except DownloadError:
            raise
        except Exception as exc:
            raise DownloadError(f"year {year}: B3 request failed: {exc}") from exc
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise DownloadError(f"year {year}: B3 response is not valid Base64") from exc
        validate_csv(content, year)
        return content

