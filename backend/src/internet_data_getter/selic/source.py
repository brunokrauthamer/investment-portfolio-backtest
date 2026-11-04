"""Browser-driven client for the BCB SGS series 11 chart and values table."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
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


def _table_rows(driver) -> tuple[tuple[str, ...], ...]:
    rows = []
    for tr in driver.find_elements("css selector", "#valoresSeries tr"):
        cells = tuple(
            cell.text.strip()
            for cell in tr.find_elements("css selector", "th, td")
        )
        if cells:
            rows.append(cells)
    return tuple(rows)


def _table_text(driver) -> str:
    return driver.find_element("id", "valoresSeries").text


def _identifies_series_11(metadata: str) -> bool:
    entries = [
        line.strip()
        for line in metadata.splitlines()
        if _SERIES_ENTRY.match(line.strip())
    ]
    return len(entries) == 1 and _SERIES_LABEL.match(entries[0]) is not None


def _verify_values_page(
    driver, expected_period: str, *, require_header: bool = True
) -> tuple[tuple[Observation, ...], int]:
    metadata = driver.find_element("id", "seriesSelecionadas").text
    if not _identifies_series_11(metadata):
        raise SourceError("the BCB result does not identify SGS series 11 Selic")
    values_text = _table_text(driver)
    rows = _table_rows(driver)
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


def _set_date_filter(driver, element_id: str, formatted_date: str) -> None:
    field = driver.find_element("id", element_id)
    field.clear()
    field.send_keys(formatted_date.replace("/", ""))
    actual_date = field.get_attribute("value").strip()
    if actual_date != formatted_date:
        raise SourceError(
            f"BCB date filter {element_id} is {actual_date!r}, "
            f"expected {formatted_date!r}"
        )


def _successful_post_status(driver, method_fragment: str, timeout_ms: int) -> int:
    """Wait for Selenium's Chrome performance log to confirm the source POST."""
    from selenium.webdriver.support.ui import WebDriverWait

    requests: dict[str, str] = {}

    def find_response(browser):
        for entry in browser.get_log("performance"):
            try:
                event = json.loads(entry["message"])["message"]
            except (KeyError, TypeError, ValueError):
                continue
            params = event.get("params", {})
            request_id = params.get("requestId")
            if event.get("method") == "Network.requestWillBeSent":
                request = params.get("request", {})
                url = request.get("url", "")
                if request.get("method") == "POST" and method_fragment in url:
                    requests[request_id] = url
            elif (
                event.get("method") == "Network.responseReceived"
                and request_id in requests
            ):
                status = int(params.get("response", {}).get("status", 0))
                if not 200 <= status < 400:
                    raise SourceError(
                        f"the BCB {method_fragment} request returned HTTP {status}"
                    )
                return status
        return False

    try:
        return WebDriverWait(
            driver, timeout_ms / 1000, poll_frequency=0.1
        ).until(find_response)
    except SourceError:
        raise
    except Exception as exc:
        raise SourceError(
            f"the BCB {method_fragment} POST did not complete successfully: {exc}"
        ) from exc


class SgsSelicClient:
    """Use Selenium and headless Chrome to scrape every SGS values page."""

    def __init__(
        self,
        *,
        driver_factory: Callable | None = None,
        pacing_seconds: float = DEFAULT_PACING_SECONDS,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ):
        self._driver_factory = driver_factory
        self._pacing_seconds = pacing_seconds
        self._timeout_ms = timeout_ms

    def fetch(self) -> SourceResult:
        try:
            from selenium import webdriver
            from selenium.webdriver.support.ui import WebDriverWait
        except ImportError as exc:
            raise SourceError(
                "Selenium is required; install backend requirements and ensure Chrome "
                "is available. Selenium Manager may need network access to resolve "
                "a matching driver on the first run."
            ) from exc

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_experimental_option(
            "prefs", {"intl.accept_languages": "en-US,en"}
        )
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        observations: list[Observation] = []
        driver = None
        try:
            factory = self._driver_factory or (
                lambda chrome_options: webdriver.Chrome(options=chrome_options)
            )
            driver = factory(options)
            driver.set_page_load_timeout(self._timeout_ms / 1000)
            driver.execute_cdp_cmd("Network.enable", {})
            driver.get(CHART_URL)
            wait = WebDriverWait(driver, self._timeout_ms / 1000, poll_frequency=0.1)
            selected = wait.until(
                lambda browser: (
                    element.text
                    if (element := browser.find_element("id", "seriesSelecionadas")).is_displayed()
                    else False
                )
            )
            if not _identifies_series_11(selected):
                raise SourceError("the chart does not identify SGS series 11 Selic")
            if UNIT.casefold() not in selected.casefold():
                raise SourceError("the chart does not identify the % p.d. unit")
            dates = [parse_date(item) for item in _DATE_TOKEN.findall(selected)]
            if len(dates) < 2:
                raise SourceError("the chart does not show its latest available date")
            latest_date = dates[-1]
            latest_text = latest_date.strftime("%d/%m/%Y")

            _set_date_filter(driver, "dataInicio", START_FILTER)
            _set_date_filter(driver, "dataFim", latest_text)

            chart_frame = wait.until(
                lambda browser: (
                    element
                    if (element := browser.find_element("id", "frmGraficoAlt")).is_displayed()
                    else False
                )
            )
            driver.switch_to.frame(chart_frame)
            wait.until(
                lambda browser: (
                    element
                    if (element := browser.find_element("tag name", "form")).is_displayed()
                    else False
                )
            )
            driver.switch_to.default_content()

            driver.find_element(
                "css selector", "input.botao[value='Refresh chart']"
            ).click()
            _successful_post_status(driver, "atualizarGraficoEstatico", self._timeout_ms)
            driver.switch_to.frame(chart_frame)
            chart_image = wait.until(
                lambda browser: (
                    element
                    if (element := browser.find_element("tag name", "img")).is_displayed()
                    else False
                )
            )
            if not wait.until(
                lambda browser: browser.execute_script(
                    "return arguments[0].complete && arguments[0].naturalWidth > 0",
                    chart_image,
                )
            ):
                raise SourceError("the BCB refreshed chart did not finish rendering")
            driver.switch_to.default_content()
            driver.find_element(
                "css selector", "input.botao[value='View values from chart']"
            ).click()
            wait.until(
                lambda browser: browser.find_element(
                    "id", "valoresSeries"
                ).is_displayed()
            )

            seen_pages: set[tuple[tuple[date, str], ...]] = set()
            expected_count: int | None = None
            for _ in range(1000):
                page_rows, page_count = _verify_values_page(
                    driver, latest_text, require_header=expected_count is None
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
                next_links = driver.find_elements("link text", "Next")
                if not next_links:
                    if len(observations) != expected_count:
                        raise SourceError("BCB ended pagination before all observations were read")
                    break
                if len(observations) == expected_count:
                    raise SourceError("BCB pagination continues after reported count was reached")
                if self._pacing_seconds:
                    time.sleep(self._pacing_seconds)
                prior_table_id = driver.find_element("id", "valoresSeries").id
                next_links[0].click()
                wait.until(
                    lambda browser: browser.find_element(
                        "id", "valoresSeries"
                    ).id != prior_table_id
                )
                _successful_post_status(driver, "method=getPagina", self._timeout_ms)
            else:
                raise SourceError("BCB pagination exceeded the safe 1000-page limit")
        except SourceError:
            raise
        except Exception as exc:
            raise SourceError(f"BCB chart request or pagination failed: {exc}") from exc
        finally:
            if driver is not None:
                driver.quit()

        assert expected_count is not None
        validated = validate_observations(observations, latest_date, expected_count)
        return SourceResult(validated, latest_date, expected_count)
