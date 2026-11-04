"""Yahoo Finance HTML source for daily S&P 500 adjusted closing values."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from email.message import Message
import re
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


SYMBOL = "^GSPC"
SOURCE_URL = "https://finance.yahoo.com/quote/%5EGSPC/history/"
TERMS_URL = "https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html"
DEFAULT_START_DATE = date(2011, 1, 3)
DEFAULT_TIMEOUT_SECONDS = 30
_USER_AGENT = "Mozilla/5.0 (compatible; HistoricalDataGetter/1.0)"
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_DATE = re.compile(r"^([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})$")
_DATE_LIKE = re.compile(r"^(?:[A-Za-z]{3}\s+\d{1,2}|\d{1,4}[-/.]\d{1,2})")
_PRICE = re.compile(r"^(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$")
_EMPTY_SOURCE = re.compile(r"\b(?:no historical data(?: found| available)?|no data found|no data available|no results for this time period)\b", re.IGNORECASE)
_PAGING_TEXT = re.compile(
    r"^(?:(?:show|load)\s+more(?:\s+historical)?(?:\s+data)?|next(?:\s+page)?|previous(?:\s+page)?)$",
    re.IGNORECASE,
)
_SYMBOL_TOKEN = re.compile(r"(?<![A-Za-z0-9])\^GSPC(?![A-Za-z0-9])", re.IGNORECASE)
_IDENTITY_TICKER = re.compile(r"\^[A-Z][A-Z0-9.-]*", re.IGNORECASE)
_ACTION_ROW = re.compile(r"^(?:dividend|stock split)$", re.IGNORECASE)


class SourceError(RuntimeError):
    """Yahoo did not return a complete, identifiable S&P 500 history page."""


@dataclass(frozen=True, order=True)
class Observation:
    date: date
    adjusted_close: str


@dataclass(frozen=True)
class PageResult:
    observations: tuple[Observation, ...]
    start_date: date
    end_date: date
    source_url: str


def _as_date(value: date | str, name: str) -> date:
    if isinstance(value, datetime):
        raise SourceError(f"{name} must be a calendar date, not a datetime")
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise SourceError(f"{name} must use YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SourceError(f"{name} must use YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise SourceError(f"{name} must use YYYY-MM-DD")
    return parsed


def parse_date_bound(value: date | str, name: str = "date") -> date:
    """Validate a caller-provided ISO calendar date."""
    return _as_date(value, name)


def build_history_url(start_date: date | str, end_date: date | str) -> str:
    """Build a Yahoo page URL for an inclusive date range using UTC bounds."""
    start = _as_date(start_date, "start date")
    end = _as_date(end_date, "end date")
    if start > end:
        raise SourceError("start date must not be after end date")
    start_seconds = int(datetime.combine(start, time.min, tzinfo=timezone.utc).timestamp())
    end_seconds = int(
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc).timestamp()
    )
    query = urlencode(
        {
            "period1": start_seconds,
            "period2": end_seconds,
            "interval": "1d",
            "filter": "history",
            "frequency": "1d",
            "includeAdjustedClose": "true",
            "lang": "en-US",
            "region": "US",
        }
    )
    return f"{SOURCE_URL}?{query}"


def validate_history_request_url(history_url: str, start_date: date | str, end_date: date | str) -> None:
    """Require a final Yahoo URL to retain the requested source and data selection."""
    expected = urlsplit(build_history_url(start_date, end_date))
    try:
        actual = urlsplit(history_url)
        expected_query = parse_qs(expected.query, strict_parsing=True)
        actual_query = parse_qs(actual.query, strict_parsing=True)
    except (TypeError, ValueError) as exc:
        raise SourceError("Yahoo response has an invalid final history URL") from exc
    same_source = (
        actual.scheme.casefold() == expected.scheme.casefold()
        and actual.netloc.casefold() == expected.netloc.casefold()
        and unquote(actual.path).casefold() == unquote(expected.path).casefold()
    )
    same_bounds = all(
        len(actual_query.get(key, [])) == 1
        and actual_query[key] == expected_query[key]
        for key in ("period1", "period2")
    )
    if not same_source or not same_bounds:
        raise SourceError("redirected Yahoo history URL does not match requested bounds")
    selection_keys = ("interval", "filter", "frequency", "includeAdjustedClose")
    same_selection = all(
        len(actual_query.get(key, [])) == 1
        and actual_query[key] == expected_query[key]
        for key in selection_keys
    )
    if not same_selection:
        raise SourceError("redirected Yahoo history URL does not match requested selection")


def _parse_source_date(value: str) -> date:
    match = _DATE.fullmatch(value.strip())
    if not match:
        raise ValueError(value)
    month_text, day_text, year_text = match.groups()
    month = _MONTHS.get(month_text.casefold())
    if month is None:
        raise ValueError(value)
    return date(int(year_text), month, int(day_text))


def _parse_price(value: str) -> str:
    text = value.strip()
    if not _PRICE.fullmatch(text):
        raise SourceError(f"invalid or missing adjusted close: {text!r}")
    return text.replace(",", "")


def _header_indexes(table) -> tuple[int, int] | None:
    header = table.find("thead")
    if header is None:
        return None
    cells = header.find_all(["th", "td"])
    labels = [" ".join(cell.stripped_strings) for cell in cells]
    dates = [index for index, value in enumerate(labels) if value.strip().casefold() == "date"]
    adjusted = [
        index for index, value in enumerate(labels)
        if re.match(r"^adj\s*close\b", value.strip(), re.IGNORECASE)
    ]
    if not dates and not adjusted:
        return None
    if len(dates) != 1 or len(adjusted) != 1:
        raise SourceError("history table must have unique Date and Adj Close columns")
    return dates[0], adjusted[0]


def _identity_fields(soup) -> tuple[str, ...]:
    title = soup.find("title")
    heading = soup.find("h1")
    return tuple(
        value.get_text(" ", strip=True)
        for value in (title, heading)
        if value is not None
    )


def _validate_identity(soup) -> None:
    fields = _identity_fields(soup)
    if not any(_SYMBOL_TOKEN.search(value) for value in fields):
        raise SourceError("Yahoo page does not identify ^GSPC")
    explicit_tickers = {
        match.group(0).casefold()
        for value in fields
        for match in _IDENTITY_TICKER.finditer(value)
    }
    if any(value != SYMBOL.casefold() for value in explicit_tickers):
        raise SourceError("Yahoo page has conflicting Yahoo ticker identity fields")


def parse_history_page(
    html: str,
    start_date: date | str,
    end_date: date | str,
    *,
    source_url: str | None = None,
) -> PageResult:
    """Validate the complete Yahoo page and extract ascending adjusted closes."""
    start = _as_date(start_date, "start date")
    end = _as_date(end_date, "end date")
    if start > end:
        raise SourceError("start date must not be after end date")
    if not isinstance(html, str) or not html.strip():
        raise SourceError("Yahoo returned an empty HTML response")
    if not re.search(r"</html\s*>\s*$", html, re.IGNORECASE):
        raise SourceError("Yahoo HTML response appears truncated")

    soup = BeautifulSoup(html, "html.parser")
    _validate_identity(soup)

    candidate_tables = []
    for table in soup.find_all("table"):
        indexes = _header_indexes(table)
        if indexes is not None:
            candidate_tables.append((table, indexes))
    if len(candidate_tables) != 1:
        visible_text = soup.body.get_text(" ", strip=True) if soup.body else soup.get_text(" ", strip=True)
        if not candidate_tables and _EMPTY_SOURCE.search(visible_text):
            return PageResult((), start, end, source_url or build_history_url(start, end))
        raise SourceError("Yahoo history page must contain one table with Date and Adj Close columns")
    table, (date_index, adjusted_index) = candidate_tables[0]

    observations: list[Observation] = []
    for row in table.select("tbody tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        if not cells:
            continue
        if (
            len(cells) == 1
            and cells[0].has_attr("colspan")
            and _ACTION_ROW.fullmatch(cells[0].get_text(" ", strip=True))
        ):
            continue
        date_text = cells[date_index].get_text(" ", strip=True) if date_index < len(cells) else ""
        price_text = cells[adjusted_index].get_text(" ", strip=True) if adjusted_index < len(cells) else ""
        if max(date_index, adjusted_index) >= len(cells):
            if _DATE_LIKE.match(date_text):
                raise SourceError(f"malformed observation row for {date_text!r}")
            continue

        try:
            observation_date = _parse_source_date(date_text)
        except ValueError as exc:
            if _DATE_LIKE.match(date_text) or _PRICE.fullmatch(price_text):
                raise SourceError(f"malformed observation date: {date_text!r}") from exc
            continue
        if not start <= observation_date <= end:
            raise SourceError(f"observation {observation_date} is outside requested interval")
        observations.append(Observation(observation_date, _parse_price(price_text)))

    if not observations:
        visible_text = soup.body.get_text(" ", strip=True) if soup.body else soup.get_text(" ", strip=True)
        if _EMPTY_SOURCE.search(visible_text):
            return PageResult((), start, end, source_url or build_history_url(start, end))
        raise SourceError("Yahoo history page contains no recognizable data rows")

    dates = [item.date for item in observations]
    if len(set(dates)) != len(dates):
        raise SourceError("Yahoo page contains a duplicated observation date")
    observations.sort(key=lambda item: item.date)
    return PageResult(tuple(observations), start, end, source_url or build_history_url(start, end))


class YahooFinanceClient:
    """Fetch one historical interval from Yahoo using its ordinary HTTPS page."""

    def __init__(
        self,
        *,
        opener: Callable | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._opener = opener or urlopen
        self._timeout = timeout

    def fetch(self, start_date: date | str, end_date: date | str) -> PageResult:
        url = build_history_url(start_date, end_date)
        request = Request(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "text/html"},
        )
        try:
            with self._opener(request, timeout=self._timeout) as response:
                status = getattr(response, "status", 200)
                if not 200 <= status < 300:
                    raise SourceError(f"Yahoo history request returned HTTP {status}")
                headers = getattr(response, "headers", None)
                content_type = headers.get("Content-Type", "text/html") if headers else "text/html"
                if "text/html" not in content_type.casefold():
                    raise SourceError(f"Yahoo history response was not HTML: {content_type}")
                charset = headers.get_content_charset() if isinstance(headers, Message) else None
                body = response.read()
                try:
                    html = body.decode(charset or "utf-8")
                except (LookupError, UnicodeDecodeError) as exc:
                    raise SourceError("Yahoo history response has an unsupported character encoding") from exc
                final_url = response.geturl() if hasattr(response, "geturl") else url
        except SourceError:
            raise
        except HTTPError as exc:
            raise SourceError(f"Yahoo history request returned HTTP {exc.code}") from exc
        except (URLError, OSError, TimeoutError) as exc:
            raise SourceError(f"Yahoo history request failed: {exc}") from exc
        validate_history_request_url(final_url, start_date, end_date)
        return parse_history_page(
            html, start_date, end_date, source_url=final_url
        )
