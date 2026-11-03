"""Browser-driven client for the BCB SGS series 11 chart and values table."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
import time
from typing import Callable, Iterable


CHART_URL = (
    "https://www3.bcb.gov.br/sgspub/consultarvalores/"
    "consultarValoresSeries.do?method=consultarGraficoPorId&hdOidSeriesSelecionadas=11"
)
DATASET_URL = "https://dadosabertos.bcb.gov.br/dataset/11-taxa-de-juros---selic"
SERIES_ID = 11
UNIT = "% p.d."
START_FILTER = "01/01/2011"
DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_PACING_SECONDS = 0.2
_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_DATE_LIKE = re.compile(r"^\d{1,4}[-./]\d{1,2}[-./]\d{2,4}$")
_DECIMAL = re.compile(r"^\d+(?:,\d+)?$")
_RATE_LIKE = re.compile(r"^\d+(?:[,.]\d+)?$")
_DATE_TOKEN = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
_COUNT = re.compile(r"Found registers by series\s*:\s*([\d.]+)", re.IGNORECASE)
_SERIES_LABEL = re.compile(
    r"^11(?:\s*-\s*|\s+)(?:interest rate|taxa de juros)\s*-\s*selic\b",
    re.IGNORECASE,
)
_SERIES_ENTRY = re.compile(r"^\d+(?:\s*-\s*|\s+)")
_DATE_HEADER = re.compile(r"(?:date|data)(?:\s+dd/mm/yyyy)?", re.IGNORECASE)
_SERIES_HEADER = re.compile(r"11\s*%\s*p\.d\.", re.IGNORECASE)


class SourceError(RuntimeError):
    """The BCB chart did not provide a complete, identifiable values table."""


@dataclass(frozen=True)
class Observation:
    date: date
    rate: str


@dataclass(frozen=True)
class SourceResult:
    observations: tuple[Observation, ...]
    latest_date: date
    reported_count: int


def parse_date(value: str) -> date:
    if not _DATE.fullmatch(value):
        raise SourceError(f"invalid BCB date: {value!r}")
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError as exc:
        raise SourceError(f"invalid BCB date: {value!r}") from exc


def parse_rate(value: str) -> str:
    """Convert the source's comma decimal separator without changing precision."""
    text = value.strip()
    if not _DECIMAL.fullmatch(text):
        raise SourceError(f"invalid BCB percentage: {value!r}")
    return text.replace(",", ".")


def parse_observation_rows(rows: Iterable[Iterable[str]]) -> tuple[Observation, ...]:
    observations: list[Observation] = []
    for cells in rows:
        row = [str(cell).strip() for cell in cells]
        if not row:
            continue
        first_cell = row[0] if row else ""
        if not first_cell:
            if len(row) > 1 and _RATE_LIKE.fullmatch(row[1]):
                raise SourceError("malformed observation date in numeric-rate row")
            continue  # headers, source footer and pagination are not observations
        if not _DATE.fullmatch(first_cell):
            if _DATE_LIKE.fullmatch(first_cell) or (
                len(row) > 1 and _RATE_LIKE.fullmatch(row[1])
            ):
                raise SourceError(f"malformed observation date: {first_cell!r}")
            continue  # headers, source footer and pagination are not observations
        if len(row) != 2:
            raise SourceError(f"malformed observation row for {first_cell}")
        observations.append(Observation(parse_date(first_cell), parse_rate(row[1])))
    return tuple(observations)


def parse_reported_count(table_text: str) -> int:
    match = _COUNT.search(table_text)
    if not match:
        raise SourceError("the BCB values table does not report its observation count")
    count = int(match.group(1).replace(".", ""))
    if count < 1:
        raise SourceError("the BCB values table reports no observations")
    return count


def validate_observations(
    observations: Iterable[Observation], latest_date: date, reported_count: int
) -> tuple[Observation, ...]:
    values = tuple(observations)
    if not values:
        raise SourceError("the BCB values table contains no observations")
    if len(values) != reported_count:
        raise SourceError(
            f"BCB reported {reported_count} observations but {len(values)} were read"
        )
    dates = [item.date for item in values]
    if any(later <= earlier for earlier, later in zip(dates, dates[1:])):
        raise SourceError("BCB observations are duplicated or out of date order")
    if dates[0].year != 2011:
        raise SourceError(f"first BCB observation is {dates[0]}, expected a date in 2011")
    if dates[-1] != latest_date:
        raise SourceError(
            f"last BCB observation is {dates[-1]}, source latest date is {latest_date}"
        )
    return values


def _table_rows(page) -> tuple[tuple[str, ...], ...]:
    rows = []
    for tr in page.locator("#valoresSeries tr").all():
        cells = tuple(cell.strip() for cell in tr.locator("th, td").all_inner_texts())
        if cells:
            rows.append(cells)
    return tuple(rows)


def _table_text(page) -> str:
    return page.locator("#valoresSeries").inner_text()


def _identifies_series_11(metadata: str) -> bool:
    entries = [
        line.strip()
        for line in metadata.splitlines()
        if _SERIES_ENTRY.match(line.strip())
    ]
    return len(entries) == 1 and _SERIES_LABEL.match(entries[0]) is not None


def _verify_values_page(
    page, expected_period: str, *, require_header: bool = True
) -> tuple[tuple[Observation, ...], int]:
    metadata = page.locator("#seriesSelecionadas").inner_text()
    if not _identifies_series_11(metadata):
        raise SourceError("the BCB result does not identify SGS series 11 Selic")
    values_text = _table_text(page)
    rows = _table_rows(page)
    header = next(
        (row for row in rows if len(row) == 2 and _DATE_HEADER.fullmatch(row[0])), None
    )
    if (require_header and header is None) or (
        header is not None and not _SERIES_HEADER.fullmatch(header[1])
    ):
        raise SourceError("the BCB values table column header does not identify exact series 11 % p.d.")
    period_dates = _DATE_TOKEN.findall(metadata)
    if len(period_dates) < 2:
        raise SourceError("the BCB values table does not confirm the requested period")
    start, end = parse_date(period_dates[0]), parse_date(period_dates[1])
    expected_end = parse_date(expected_period)
    if start != date(2011, 1, 1) or end != expected_end:
        raise SourceError("the BCB values table period differs from the requested range")
    if not re.search(r"\bLinear\b", metadata, re.IGNORECASE):
        raise SourceError("the BCB values table is not using the Linear function")
    if UNIT.casefold() not in values_text.casefold():
        raise SourceError("the BCB values table does not identify its % p.d. unit")
    return parse_observation_rows(rows), parse_reported_count(values_text)


class SgsSelicClient:
    """Use the visible SGS chart controls and page through every value row."""

    def __init__(
        self,
        *,
        playwright_factory: Callable | None = None,
        pacing_seconds: float = DEFAULT_PACING_SECONDS,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ):
        self._playwright_factory = playwright_factory
        self._pacing_seconds = pacing_seconds
        self._timeout_ms = timeout_ms

    def fetch(self) -> SourceResult:
        try:
            factory = self._playwright_factory
            if factory is None:
                from playwright.sync_api import sync_playwright

                factory = sync_playwright
        except ImportError as exc:
            raise SourceError(
                "Playwright is required; install backend requirements and run "
                "python -m playwright install chromium"
            ) from exc

        observations: list[Observation] = []
        try:
            with factory() as runtime:
                browser = runtime.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.set_default_timeout(self._timeout_ms)
                    page.goto(CHART_URL, wait_until="domcontentloaded")
                    selected = page.locator("#seriesSelecionadas").inner_text()
                    if not _identifies_series_11(selected):
                        raise SourceError("the chart does not identify SGS series 11 Selic")
                    if UNIT.casefold() not in selected.casefold():
                        raise SourceError("the chart does not identify the % p.d. unit")
                    dates = [parse_date(item) for item in _DATE_TOKEN.findall(selected)]
                    if len(dates) < 2:
                        raise SourceError("the chart does not show its latest available date")
                    latest_date = dates[-1]
                    latest_text = latest_date.strftime("%d/%m/%Y")

                    page.locator("#dataInicio").fill(START_FILTER)
                    page.locator("#dataFim").fill(latest_text)
                    page.frame_locator("#frmGraficoAlt").locator("form").first.wait_for(
                        state="attached", timeout=self._timeout_ms
                    )
                    with page.expect_response(
                        lambda response: response.request.method == "POST"
                        and "atualizarGraficoEstatico" in response.url,
                        timeout=self._timeout_ms,
                    ) as refresh_response:
                        page.locator("input.botao[value='Refresh chart']").click()
                    if not 200 <= refresh_response.value.status < 400:
                        raise SourceError(
                            f"the BCB chart refresh returned HTTP {refresh_response.value.status}"
                        )
                    chart_image = page.frame_locator("#frmGraficoAlt").locator("img")
                    chart_image.wait_for(state="visible", timeout=self._timeout_ms)
                    if not chart_image.evaluate("image => image.complete && image.naturalWidth > 0"):
                        raise SourceError("the BCB refreshed chart did not finish rendering")
                    page.locator("input.botao[value='View values from chart']").click()

                    seen_pages: set[tuple[tuple[date, str], ...]] = set()
                    expected_count: int | None = None
                    for _ in range(1000):
                        page_rows, page_count = _verify_values_page(
                            page, latest_text, require_header=expected_count is None
                        )
                        if expected_count is None:
                            expected_count = page_count
                        elif page_count != expected_count:
                            raise SourceError("BCB changed the reported observation count while paging")
                        signature = tuple((row.date, row.rate) for row in page_rows)
                        if not signature:
                            raise SourceError("the BCB values page contains no observations")
                        if signature in seen_pages:
                            raise SourceError("BCB repeated a values page while pagination was active")
                        seen_pages.add(signature)
                        observations.extend(page_rows)
                        if len(observations) > expected_count:
                            raise SourceError("BCB returned more rows than its reported count")
                        next_link = page.get_by_role("link", name="Next", exact=True)
                        if next_link.count() == 0:
                            if len(observations) != expected_count:
                                raise SourceError("BCB ended pagination before all observations were read")
                            break
                        if len(observations) == expected_count:
                            raise SourceError("BCB pagination continues after reported count was reached")
                        if self._pacing_seconds:
                            time.sleep(self._pacing_seconds)
                        with page.expect_response(
                            lambda response: response.request.method == "POST"
                            and "method=getPagina" in response.url,
                            timeout=self._timeout_ms,
                        ) as page_response:
                            with page.expect_navigation(
                                wait_until="domcontentloaded", timeout=self._timeout_ms
                            ):
                                next_link.first.click()
                        if not 200 <= page_response.value.status < 400:
                            raise SourceError(
                                f"the BCB next-page request returned HTTP {page_response.value.status}"
                            )
                    else:
                        raise SourceError("BCB pagination exceeded the safe 1000-page limit")
                finally:
                    browser.close()
        except SourceError:
            raise
        except Exception as exc:
            raise SourceError(f"BCB chart request or pagination failed: {exc}") from exc

        assert expected_count is not None
        validated = validate_observations(observations, latest_date, expected_count)
        return SourceResult(validated, latest_date, expected_count)
