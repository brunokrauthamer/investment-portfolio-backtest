from __future__ import annotations

from datetime import date, datetime, timezone
from email.message import Message
from contextlib import redirect_stdout
from io import StringIO
from io import BytesIO
import json
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from unittest.mock import patch


HISTORY_HTML = """<!doctype html>
<html><head><title>S&amp;P 500 (^GSPC) Historical Data</title></head>
<body><h1>S&amp;P 500 (^GSPC)</h1>
<table data-test="historical-prices"><thead><tr>
<th>Date</th><th>Open</th><th>High</th><th>Low</th><th>Close</th>
<th>Adj Close</th><th>Volume</th></tr></thead><tbody>
<tr><td>Jan 4, 2011</td><td>1,273.02</td><td>1,275.92</td><td>1,259.82</td><td>1,270.20</td><td>1,270.20</td><td>4,455,700,000</td></tr>
<tr><td>Jan 3, 2011</td><td>1,257.62</td><td>1,276.17</td><td>1,257.62</td><td>1,271.87</td><td>1,271.870000</td><td>4,286,670,000</td></tr>
</tbody></table></body></html>"""


def history_html(rows: str, *, title: str = "S&P 500 (^GSPC) Historical Data", header: str = "<th>Adj Close</th>") -> str:
    return f"""<html><head><title>{title}</title></head><body>
    <h1>{title}</h1><table data-test="historical-prices"><thead><tr>
    <th>Date</th><th>Close</th>{header}</tr></thead><tbody>{rows}</tbody></table></body></html>"""


def page_result(start: date, end: date, values: list[tuple[date, str]]):
    from backend.src.internet_data_getter.sp500.source import Observation, PageResult, build_history_url

    return PageResult(
        tuple(Observation(day, price) for day, price in values),
        start,
        end,
        build_history_url(start, end),
    )


class _Response:
    status = 200

    def __init__(self, body: str, url: str):
        self.body = body.encode("utf-8")
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = "text/html; charset=utf-8"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body

    def geturl(self):
        return self.url


class SourceTests(unittest.TestCase):
    def test_url_uses_midnight_utc_and_exclusive_day_after_end(self):
        from backend.src.internet_data_getter.sp500.source import build_history_url

        url = build_history_url(date(2011, 1, 3), date(2026, 11, 4))
        self.assertIn("period1=1294012800", url)
        self.assertIn("period2=1793836800", url)
        self.assertIn("interval=1d", url)
        self.assertIn("includeAdjustedClose=true", url)

    def test_url_range_validation_rejects_reversed_dates(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, build_history_url

        with self.assertRaisesRegex(SourceError, "start date must not be after end date"):
            build_history_url(date(2026, 11, 5), date(2026, 11, 4))

    def test_parser_selects_adjusted_close_sorts_rows_and_preserves_precision(self):
        from backend.src.internet_data_getter.sp500.source import parse_history_page

        result = parse_history_page(HISTORY_HTML, date(2011, 1, 3), date(2011, 1, 4))
        self.assertEqual(
            [(item.date.isoformat(), item.adjusted_close) for item in result.observations],
            [("2011-01-03", "1271.870000"), ("2011-01-04", "1270.20")],
        )

    def test_parser_rejects_wrong_symbol_or_missing_adjusted_close(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, parse_history_page

        with self.assertRaisesRegex(SourceError, "does not identify \\^GSPC"):
            parse_history_page(HISTORY_HTML.replace("^GSPC", "^DJI"), date(2011, 1, 3), date(2011, 1, 4))
        with self.assertRaisesRegex(SourceError, "Date and Adj Close columns"):
            parse_history_page(
                history_html("<tr><td>Jan 3, 2011</td><td>1.00</td><td>1.00</td></tr>", header="<th>Close</th>"),
                date(2011, 1, 3), date(2011, 1, 3),
            )

    def test_parser_requires_exact_ticker_identity(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, parse_history_page

        for different_symbol in ("^GSPCX", "X^GSPC"):
            with self.subTest(symbol=different_symbol), self.assertRaisesRegex(
                SourceError, "does not identify \\^GSPC"
            ):
                parse_history_page(
                    HISTORY_HTML.replace("^GSPC", different_symbol),
                    date(2011, 1, 3), date(2011, 1, 4),
                )

    def test_parser_rejects_malformed_date_price_and_duplicate_rows(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, parse_history_page

        malformed = history_html("<tr><td>Jan 3, 20x1</td><td>1.00</td><td>1.00</td></tr>")
        with self.assertRaisesRegex(SourceError, "malformed observation date"):
            parse_history_page(malformed, date(2011, 1, 3), date(2011, 1, 3))
        duplicate = history_html(
            "<tr><td>Jan 3, 2011</td><td>1.00</td><td>1.00</td></tr>" * 2
        )
        with self.assertRaisesRegex(SourceError, "duplicated observation date"):
            parse_history_page(duplicate, date(2011, 1, 3), date(2011, 1, 3))

    def test_parser_rejects_rows_outside_interval_and_unrecognized_empty_page(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, parse_history_page

        outside = history_html("<tr><td>Jan 3, 2011</td><td>1.00</td><td>1.00</td></tr>")
        with self.assertRaisesRegex(SourceError, "outside requested interval"):
            parse_history_page(outside, date(2011, 1, 4), date(2011, 1, 4))
        with self.assertRaisesRegex(SourceError, "no recognizable data rows"):
            parse_history_page(history_html(""), date(2011, 1, 8), date(2011, 1, 9))

    def test_empty_result_requires_recognizable_source_message(self):
        from backend.src.internet_data_getter.sp500.source import parse_history_page

        no_results = "<html><title>S&P 500 (^GSPC)</title><body>No historical data found</body></html>"
        parsed = parse_history_page(no_results, date(2026, 11, 7), date(2026, 11, 8))
        self.assertEqual(parsed.observations, ())

    def test_parser_rejects_detectable_pagination(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, parse_history_page

        partial = HISTORY_HTML.replace("</body>", '<button aria-label="Show More">Show More</button></body>')
        with self.assertRaisesRegex(SourceError, "indicates more historical rows"):
            parse_history_page(partial, date(2011, 1, 3), date(2011, 1, 4))

    def test_parser_rejects_next_links_and_pagination_on_no_data_pages(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, parse_history_page

        next_link = HISTORY_HTML.replace(
            "</body>", '<a rel="next" href="?page=2">Next</a></body>'
        )
        empty_pages = (
            '<html><head><title>S&amp;P 500 (^GSPC)</title></head><body>'
            'No historical data found<a rel="next" href="?page=2">Next</a></body></html>',
            '<html><head><title>S&amp;P 500 (^GSPC)</title></head><body>'
            'No historical data found<button>Show More</button></body></html>',
        )
        pages = ((next_link, date(2011, 1, 3), date(2011, 1, 4)),) + tuple(
            (html, date(2026, 11, 7), date(2026, 11, 8)) for html in empty_pages
        )
        for html, start, end in pages:
            with self.subTest(html=html), self.assertRaisesRegex(
                SourceError, "indicates more historical rows"
            ):
                parse_history_page(html, start, end)

    def test_parser_rejects_incomplete_date_like_td_and_th_rows(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, parse_history_page

        incomplete_rows = (
            "<tr><td>Jan 3, 2011</td><td>Dividend</td></tr>",
            "<tr><th>Jan 3, 2011</th></tr>",
        )
        for row in incomplete_rows:
            html = HISTORY_HTML.replace("</tbody>", row + "</tbody>")
            with self.subTest(row=row), self.assertRaisesRegex(
                SourceError, "malformed observation row"
            ):
                parse_history_page(html, date(2011, 1, 3), date(2011, 1, 4))

    def test_parser_skips_a_structurally_recognizable_corporate_action_row(self):
        from backend.src.internet_data_getter.sp500.source import parse_history_page

        action = '<tr><td colspan="7">Dividend</td></tr>'
        html = HISTORY_HTML.replace("</tbody>", action + "</tbody>")
        result = parse_history_page(html, date(2011, 1, 3), date(2011, 1, 4))
        self.assertEqual(len(result.observations), 2)

    def test_parser_rejects_truncated_html(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, parse_history_page

        truncated = HISTORY_HTML.removesuffix("</html>")
        with self.assertRaisesRegex(SourceError, "appears truncated"):
            parse_history_page(truncated, date(2011, 1, 3), date(2011, 1, 4))

    def test_client_fetches_expected_url_and_uses_returned_html(self):
        from backend.src.internet_data_getter.sp500.source import YahooFinanceClient

        urls = []

        def opener(request, timeout):
            urls.append((request.full_url, timeout, request.get_header("User-agent")))
            return _Response(HISTORY_HTML, request.full_url)

        result = YahooFinanceClient(opener=opener).fetch(date(2011, 1, 3), date(2011, 1, 4))
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0][1], 30)
        self.assertTrue(urls[0][2])
        self.assertEqual(len(result.observations), 2)

    def test_client_rejects_redirects_that_change_either_requested_bound(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, YahooFinanceClient, build_history_url

        requested = build_history_url(date(2011, 1, 3), date(2011, 1, 4))
        parsed = urlsplit(requested)
        query = dict(parse_qsl(parsed.query))
        redirects = []
        changed_start = dict(query)
        changed_start["period1"] = str(int(query["period1"]) + 86400)
        redirects.append(urlunsplit(parsed._replace(query=urlencode(changed_start))))
        changed_end = dict(query)
        changed_end["period2"] = str(int(query["period2"]) - 86400)
        redirects.append(urlunsplit(parsed._replace(query=urlencode(changed_end))))
        changed_both = dict(changed_start)
        changed_both["period2"] = changed_end["period2"]
        redirects.append(urlunsplit(parsed._replace(query=urlencode(changed_both))))

        for final_url in redirects:
            with self.subTest(final_url=final_url), self.assertRaisesRegex(
                SourceError, "redirected Yahoo history URL does not match requested bounds"
            ):
                YahooFinanceClient(
                    opener=lambda *_args, final_url=final_url, **_kwargs: _Response(HISTORY_HTML, final_url)
                ).fetch(date(2011, 1, 3), date(2011, 1, 4))

    def test_client_rejects_redirects_that_change_daily_selection_options(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, YahooFinanceClient, build_history_url

        requested = build_history_url(date(2011, 1, 3), date(2011, 1, 4))
        parsed = urlsplit(requested)
        original = dict(parse_qsl(parsed.query))
        changed_options = (
            ("interval", "1mo"),
            ("frequency", "1mo"),
            ("filter", "dividends"),
            ("includeAdjustedClose", "false"),
        )
        for key, value in changed_options:
            query = dict(original)
            query[key] = value
            final_url = urlunsplit(parsed._replace(query=urlencode(query)))
            with self.subTest(option=key), self.assertRaisesRegex(
                SourceError, "redirected Yahoo history URL does not match requested selection"
            ):
                YahooFinanceClient(
                    opener=lambda *_args, final_url=final_url, **_kwargs: _Response(HISTORY_HTML, final_url)
                ).fetch(date(2011, 1, 3), date(2011, 1, 4))

    def test_client_allows_reordered_and_innocuous_redirect_parameters(self):
        from backend.src.internet_data_getter.sp500.source import YahooFinanceClient, build_history_url

        parsed = urlsplit(build_history_url(date(2011, 1, 3), date(2011, 1, 4)))
        query = list(reversed(parse_qsl(parsed.query))) + [("utm_source", "redirect")]
        final_url = urlunsplit(parsed._replace(query=urlencode(query)))
        client = YahooFinanceClient(
            opener=lambda *_args, **_kwargs: _Response(HISTORY_HTML, final_url)
        )
        result = client.fetch(date(2011, 1, 3), date(2011, 1, 4))
        self.assertEqual(len(result.observations), 2)
        self.assertEqual(result.source_url, final_url)

    def test_parser_rejects_document_next_link_metadata(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, parse_history_page

        valid_page = HISTORY_HTML.replace(
            "</head>", '<link rel="next" href="?page=2"></head>'
        )
        empty_page = (
            '<html><head><title>S&amp;P 500 (^GSPC)</title>'
            '<link rel="next" href="?page=2"></head><body>No historical data found</body></html>'
        )
        for html, start, end in (
            (valid_page, date(2011, 1, 3), date(2011, 1, 4)),
            (empty_page, date(2026, 11, 7), date(2026, 11, 8)),
        ):
            with self.subTest(html=html), self.assertRaisesRegex(
                SourceError, "indicates more historical rows"
            ):
                parse_history_page(html, start, end)

    def test_parser_rejects_conflicting_explicit_ticker_fields(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, parse_history_page

        conflicting_fields = (
            HISTORY_HTML.replace(
                "<title>S&amp;P 500 (^GSPC) Historical Data</title>",
                "<title>Dow Jones (^DJI) Historical Data</title>",
            ),
            HISTORY_HTML.replace("<h1>S&amp;P 500 (^GSPC)</h1>", "<h1>Dow Jones (^DJI)</h1>"),
        )
        for html in conflicting_fields:
            with self.subTest(html=html), self.assertRaisesRegex(
                SourceError, "conflicting Yahoo ticker identity"
            ):
                parse_history_page(html, date(2011, 1, 3), date(2011, 1, 4))

    def test_client_rejects_non_success_and_non_html_responses(self):
        from backend.src.internet_data_getter.sp500.source import SourceError, YahooFinanceClient

        class BadResponse(_Response):
            status = 503

        with self.assertRaisesRegex(SourceError, "HTTP 503"):
            YahooFinanceClient(opener=lambda *_args, **_kwargs: BadResponse(HISTORY_HTML, "https://finance.yahoo.com"))\
                .fetch(date(2011, 1, 3), date(2011, 1, 4))


class AcquisitionAndStorageTests(unittest.TestCase):
    def test_first_acquisition_writes_date_and_adjusted_close_only(self):
        from backend.src.internet_data_getter.sp500.service import Sp500Acquisition
        from backend.src.internet_data_getter.sp500.source import parse_history_page
        from backend.src.internet_data_getter.sp500.storage import Sp500FileStore

        class Client:
            def fetch(self, start, end):
                return parse_history_page(HISTORY_HTML, start, end)

        now = datetime(2026, 11, 4, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            store = Sp500FileStore(Path(temp) / "data")
            report = Sp500Acquisition(Client(), store).run(
                start_date=date(2011, 1, 3), end_date=date(2011, 1, 4), now=now
            )
            self.assertEqual(report.status, "saved")
            self.assertEqual(report.added, 2)
            self.assertEqual(
                store.active_path.read_text(encoding="utf-8"),
                "date,adjusted_close\n2011-01-03,1271.870000\n2011-01-04,1270.20\n",
            )

    def test_cli_date_flags_and_restore_are_registered(self):
        from argparse import ArgumentParser
        from backend.src.internet_data_getter.sp500 import cli

        parser = ArgumentParser()
        subs = parser.add_subparsers(dest="operation")
        cli.register_commands(subs)
        fetch = parser.parse_args(["fetch-sp500", "--start-date", "2011-01-03", "--end-date", "2011-01-04"])
        restore = parser.parse_args(["restore-sp500", "--backup", "backups/sp500/example"])
        self.assertEqual(fetch.start_date, "2011-01-03")
        self.assertEqual(fetch.end_date, "2011-01-04")
        self.assertEqual(restore.backup, "backups/sp500/example")

    def test_cli_report_labels_the_failed_request_window(self):
        from backend.src.internet_data_getter.sp500.cli import print_report
        from backend.src.internet_data_getter.sp500.service import AcquisitionReport

        report = AcquisitionReport(
            status="failed",
            requested_windows=[{
                "start": "2011-01-03",
                "end": "2011-01-04",
                "error": "Yahoo denied request",
            }],
            errors=["Yahoo denied request"],
        )
        output = StringIO()
        with redirect_stdout(output):
            print_report(report)
        self.assertIn("Window failed: 2011-01-03 through 2011-01-04", output.getvalue())
        self.assertIn("Yahoo denied request", output.getvalue())

    def test_incremental_suffix_updates_latest_overlap_and_adds_only_missing_rows(self):
        from backend.src.internet_data_getter.sp500.service import Sp500Acquisition
        from backend.src.internet_data_getter.sp500.storage import Sp500FileStore

        class Client:
            def __init__(self, pages):
                self.pages = list(pages)
                self.calls = []

            def fetch(self, start, end):
                self.calls.append((start, end))
                return self.pages.pop(0)

        jan3, jan4, jan5, jan6 = (date(2011, 1, day) for day in (3, 4, 5, 6))
        with tempfile.TemporaryDirectory() as temp:
            store = Sp500FileStore(Path(temp) / "data")
            first_client = Client([page_result(jan3, jan4, [(jan3, "10.00"), (jan4, "11.00")])])
            first = Sp500Acquisition(first_client, store).run(
                jan3, jan4, now=datetime(2026, 1, 1, tzinfo=timezone.utc)
            )
            self.assertEqual(first.status, "saved")

            client = Client([page_result(jan4, jan6, [(jan4, "11.10"), (jan5, "12.00"), (jan6, "13.00")])])
            report = Sp500Acquisition(client, store).run(
                jan3, jan6, now=datetime(2026, 1, 2, tzinfo=timezone.utc)
            )
            self.assertTrue(report.complete)
            self.assertEqual(report.status, "updated")
            self.assertEqual((report.added, report.updated), (2, 1))
            self.assertEqual(client.calls, [(jan4, jan6)])
            self.assertEqual(
                [(item.date, item.adjusted_close) for item in store.load()],
                [(jan3, "10.00"), (jan4, "11.10"), (jan5, "12.00"), (jan6, "13.00")],
            )

    def test_earlier_backfill_and_forward_extension_fetch_only_two_intervals(self):
        from backend.src.internet_data_getter.sp500.service import Sp500Acquisition
        from backend.src.internet_data_getter.sp500.storage import Sp500FileStore

        class Client:
            def __init__(self, pages):
                self.pages, self.calls = list(pages), []

            def fetch(self, start, end):
                self.calls.append((start, end))
                return self.pages.pop(0)

        jan3, jan4, jan5, jan6 = (date(2011, 1, day) for day in (3, 4, 5, 6))
        with tempfile.TemporaryDirectory() as temp:
            store = Sp500FileStore(Path(temp) / "data")
            Sp500Acquisition(
                Client([page_result(jan4, jan5, [(jan4, "11"), (jan5, "12")])]), store
            ).run(jan4, jan5, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
            client = Client([
                page_result(jan3, jan3, [(jan3, "10")]),
                page_result(jan5, jan6, [(jan5, "12"), (jan6, "13")]),
            ])
            report = Sp500Acquisition(client, store).run(
                jan3, jan6, now=datetime(2026, 1, 2, tzinfo=timezone.utc)
            )
            self.assertEqual(report.status, "updated")
            self.assertEqual(client.calls, [(jan3, jan3), (jan5, jan6)])
            self.assertEqual(report.added, 2)

    def test_narrow_historical_request_does_not_refetch_or_drop_existing_rows(self):
        from backend.src.internet_data_getter.sp500.service import Sp500Acquisition
        from backend.src.internet_data_getter.sp500.storage import Sp500FileStore

        class Client:
            def __init__(self, pages=()):
                self.pages, self.calls = list(pages), []

            def fetch(self, start, end):
                self.calls.append((start, end))
                return self.pages.pop(0)

        jan3, jan4, jan5 = (date(2011, 1, day) for day in (3, 4, 5))
        with tempfile.TemporaryDirectory() as temp:
            store = Sp500FileStore(Path(temp) / "data")
            Sp500Acquisition(Client([page_result(jan3, jan5, [(jan3, "10"), (jan4, "11"), (jan5, "12")])]), store).run(
                jan3, jan5, now=datetime(2026, 1, 1, tzinfo=timezone.utc)
            )
            client = Client()
            report = Sp500Acquisition(client, store).run(
                jan3, jan4, now=datetime(2026, 1, 2, tzinfo=timezone.utc)
            )
            self.assertEqual(report.status, "unchanged")
            self.assertEqual(client.calls, [])
            self.assertEqual(len(store.load()), 3)

    def test_a_failed_later_request_preserves_the_existing_csv(self):
        from backend.src.internet_data_getter.sp500.service import Sp500Acquisition
        from backend.src.internet_data_getter.sp500.source import SourceError
        from backend.src.internet_data_getter.sp500.storage import Sp500FileStore

        class Client:
            def __init__(self, page=None):
                self.page = page

            def fetch(self, _start, _end):
                if self.page is None:
                    raise SourceError("Yahoo denied request")
                return self.page

        jan3, jan4 = date(2011, 1, 3), date(2011, 1, 4)
        with tempfile.TemporaryDirectory() as temp:
            store = Sp500FileStore(Path(temp) / "data")
            Sp500Acquisition(Client(page_result(jan3, jan3, [(jan3, "10")])), store).run(
                jan3, jan3, now=datetime(2026, 1, 1, tzinfo=timezone.utc)
            )
            before = store.active_path.read_bytes()
            report = Sp500Acquisition(Client(), store).run(
                jan3, jan4, now=datetime(2026, 1, 2, tzinfo=timezone.utc)
            )
            self.assertFalse(report.complete)
            self.assertEqual(report.errors, ["Yahoo denied request"])
            self.assertEqual(store.active_path.read_bytes(), before)

    def test_report_identifies_the_date_window_that_failed(self):
        from backend.src.internet_data_getter.sp500.service import Sp500Acquisition
        from backend.src.internet_data_getter.sp500.source import Observation, SourceError
        from backend.src.internet_data_getter.sp500.storage import Sp500FileStore

        class Client:
            def fetch(self, start, end):
                if start == date(2011, 1, 5):
                    raise SourceError("Yahoo denied request")
                return page_result(start, end, [(start, "10")])

        jan3, jan4, jan5, jan6 = (date(2011, 1, day) for day in (3, 4, 5, 6))
        with tempfile.TemporaryDirectory() as temp:
            store = Sp500FileStore(Path(temp) / "data")
            store.save(
                tuple(Observation(day, str(day.day)) for day in (jan4, jan5)),
                (page_result(jan4, jan5, []),),
                datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
            report = Sp500Acquisition(Client(), store).run(
                jan3, jan6, now=datetime(2026, 1, 2, tzinfo=timezone.utc)
            )
            self.assertFalse(report.complete)
            self.assertEqual(report.requested_windows[-1]["start"], "2011-01-05")
            self.assertEqual(report.requested_windows[-1]["end"], "2011-01-06")
            self.assertEqual(report.requested_windows[-1]["error"], "Yahoo denied request")

    def test_report_identifies_a_response_with_the_wrong_date_window(self):
        from backend.src.internet_data_getter.sp500.service import Sp500Acquisition
        from backend.src.internet_data_getter.sp500.source import PageResult
        from backend.src.internet_data_getter.sp500.storage import Sp500FileStore

        requested = date(2011, 1, 3)

        class WrongWindowClient:
            def fetch(self, _start, _end):
                return PageResult(
                    (), date(2011, 1, 4), date(2011, 1, 4),
                    "https://finance.yahoo.com/quote/%5EGSPC/history/?period1=1&period2=2",
                )

        with tempfile.TemporaryDirectory() as temp:
            store = Sp500FileStore(Path(temp) / "data")
            report = Sp500Acquisition(WrongWindowClient(), store).run(
                requested, requested, now=datetime(2026, 1, 1, tzinfo=timezone.utc)
            )
            self.assertFalse(report.complete)
            self.assertIn("provenance does not match", report.requested_windows[-1]["error"])

    def test_explicit_empty_window_reports_unchanged_without_inventing_rows(self):
        from backend.src.internet_data_getter.sp500.service import Sp500Acquisition
        from backend.src.internet_data_getter.sp500.source import PageResult
        from backend.src.internet_data_getter.sp500.storage import Sp500FileStore

        day = date(2026, 11, 7)

        class EmptyClient:
            def fetch(self, start, end):
                return PageResult(
                    (), start, end,
                    "https://finance.yahoo.com/quote/%5EGSPC/history/?period1=1&period2=2",
                )

        with tempfile.TemporaryDirectory() as temp:
            store = Sp500FileStore(Path(temp) / "data")
            report = Sp500Acquisition(EmptyClient(), store).run(
                day, day, now=datetime(2026, 11, 8, tzinfo=timezone.utc)
            )
            self.assertTrue(report.complete)
            self.assertEqual(report.status, "unchanged")
            self.assertEqual(report.observations, 0)
            self.assertFalse(store.active_path.exists())


class FileStoreTests(unittest.TestCase):
    def setUp(self):
        from backend.src.internet_data_getter.sp500.storage import Sp500FileStore

        self.temp = tempfile.TemporaryDirectory()
        self.store = Sp500FileStore(Path(self.temp.name) / "data")
        self.jan3 = date(2011, 1, 3)
        self.jan4 = date(2011, 1, 4)
        self.now = datetime(2026, 11, 4, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, values):
        from backend.src.internet_data_getter.sp500.source import Observation

        observations = tuple(Observation(day, price) for day, price in values)
        page = page_result(self.jan3, self.jan4, values)
        return self.store.save(observations, (page,), self.now)

    def test_save_and_load_validate_csv_manifest_pair(self):
        from backend.src.internet_data_getter.sp500.source import Observation

        self.save([(self.jan3, "1271.87")])
        self.assertEqual(self.store.active_path.read_text(encoding="utf-8"), "date,adjusted_close\n2011-01-03,1271.87\n")
        self.assertEqual(self.store.load(), (Observation(self.jan3, "1271.87"),))
        manifest = self.store.manifest_path.read_text(encoding="utf-8")
        self.assertIn('"symbol": "^GSPC"', manifest)
        self.assertIn('"observation_count": 1', manifest)

    def test_identical_data_does_not_touch_csv_or_create_backup(self):
        from backend.src.internet_data_getter.sp500.source import Observation

        observations = [(self.jan3, "1271.87")]
        self.save(observations)
        before_csv = self.store.active_path.read_bytes()
        before_csv_mtime = self.store.active_path.stat().st_mtime_ns
        before_manifest = self.store.manifest_path.read_bytes()
        before_manifest_mtime = self.store.manifest_path.stat().st_mtime_ns
        page = page_result(self.jan3, self.jan4, observations)
        result = self.store.save(
            tuple(Observation(day, price) for day, price in observations),
            (page,), datetime(2026, 11, 5, tzinfo=timezone.utc),
        )
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(self.store.active_path.read_bytes(), before_csv)
        self.assertEqual(self.store.active_path.stat().st_mtime_ns, before_csv_mtime)
        self.assertEqual(self.store.manifest_path.read_bytes(), before_manifest)
        self.assertEqual(self.store.manifest_path.stat().st_mtime_ns, before_manifest_mtime)
        self.assertFalse(self.store.pending_path.exists())
        self.assertEqual(list(self.store.backup_root.glob("*")), [])

    def test_load_rejects_missing_or_inconsistent_request_provenance(self):
        from backend.src.internet_data_getter.sp500.storage import ManifestError

        self.save([(self.jan3, "1271.87")])
        original = json.loads(self.store.manifest_path.read_text(encoding="utf-8"))

        def change_window_bound(window, key, amount):
            parsed = urlsplit(window["source_url"])
            query = dict(parse_qsl(parsed.query))
            query[key] = str(int(query[key]) + amount)
            window["source_url"] = urlunsplit(parsed._replace(query=urlencode(query)))

        def change_window_option(window, key, value):
            parsed = urlsplit(window["source_url"])
            query = dict(parse_qsl(parsed.query))
            query[key] = value
            window["source_url"] = urlunsplit(parsed._replace(query=urlencode(query)))

        cases = {
            "missing requested windows": lambda current: current.pop("requested_windows"),
            "empty requested windows": lambda current: current.update(requested_windows=[]),
            "missing retrieval timestamp": lambda current: current.pop("retrieved_at"),
            "malformed retrieval timestamp": lambda current: current.update(retrieved_at="2026-11-04Z"),
            "missing requested start": lambda current: current.pop("requested_start"),
            "missing requested end": lambda current: current.pop("requested_end"),
            "window period1 changed": lambda current: change_window_bound(
                current["requested_windows"][0], "period1", 86400
            ),
            "window period2 changed": lambda current: change_window_bound(
                current["requested_windows"][0], "period2", -86400
            ),
            "window interval changed": lambda current: change_window_option(
                current["requested_windows"][0], "interval", "1mo"
            ),
            "window frequency changed": lambda current: change_window_option(
                current["requested_windows"][0], "frequency", "1mo"
            ),
            "window filter changed": lambda current: change_window_option(
                current["requested_windows"][0], "filter", "dividends"
            ),
            "adjusted close disabled": lambda current: change_window_option(
                current["requested_windows"][0], "includeAdjustedClose", "false"
            ),
            "requested start disagrees with windows": lambda current: current.update(
                requested_start="2011-01-04"
            ),
            "requested end disagrees with windows": lambda current: current.update(
                requested_end="2011-01-03"
            ),
        }
        for label, mutate in cases.items():
            with self.subTest(variant=label):
                manifest = json.loads(json.dumps(original))
                mutate(manifest["current"])
                self.store.manifest_path.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaises(ManifestError):
                    self.store.load()

    def test_recovery_preserves_candidate_and_journal_when_new_pair_is_inconsistent(self):
        from backend.src.internet_data_getter.sp500 import storage
        from backend.src.internet_data_getter.sp500.source import Observation
        from backend.src.internet_data_getter.sp500.storage import ManifestError, Sp500FileStore

        def save(store, values):
            page = page_result(self.jan3, self.jan4, values)
            return store.save(tuple(Observation(day, price) for day, price in values), (page,), self.now)

        for committed_manifest in (False, True):
            with self.subTest(committed_manifest=committed_manifest), tempfile.TemporaryDirectory() as temp:
                store = Sp500FileStore(Path(temp) / "data")
                save(store, [(self.jan3, "1271.87")])
                atomic_write = storage._atomic_write

                def interrupt_manifest(path, content):
                    if path == store.manifest_path:
                        raise OSError("simulated interruption after CSV replacement")
                    atomic_write(path, content)

                with patch("backend.src.internet_data_getter.sp500.storage._atomic_write", side_effect=interrupt_manifest):
                    with self.assertRaisesRegex(OSError, "after CSV replacement"):
                        save(store, [(self.jan3, "1271.88"), (self.jan4, "1270.20")])

                pending = json.loads(store.pending_path.read_text(encoding="utf-8"))
                pending["new_manifest"]["current"]["observation_count"] += 1
                candidate_manifest_bytes = store._manifest_bytes(pending["new_manifest"])
                pending["new_manifest_sha256"] = storage.sha256(candidate_manifest_bytes)
                if committed_manifest:
                    store.manifest_path.write_bytes(candidate_manifest_bytes)
                store.pending_path.write_text(json.dumps(pending, indent=2), encoding="utf-8")
                active_before = store.active_path.read_bytes()
                manifest_before = store.manifest_path.read_bytes()
                pending_before = store.pending_path.read_bytes()

                with self.assertRaisesRegex(ManifestError, "observation count does not match"):
                    store.load()

                self.assertEqual(store.active_path.read_bytes(), active_before)
                self.assertEqual(store.manifest_path.read_bytes(), manifest_before)
                self.assertEqual(store.pending_path.read_bytes(), pending_before)

    def test_recovery_preserves_old_pair_and_journal_when_rollback_pair_is_inconsistent(self):
        from backend.src.internet_data_getter.sp500 import storage
        from backend.src.internet_data_getter.sp500.source import Observation
        from backend.src.internet_data_getter.sp500.storage import ManifestError, Sp500FileStore

        with tempfile.TemporaryDirectory() as temp:
            store = Sp500FileStore(Path(temp) / "data")

            def save(values):
                page = page_result(self.jan3, self.jan4, values)
                return store.save(tuple(Observation(day, price) for day, price in values), (page,), self.now)

            save([(self.jan3, "1271.87")])
            atomic_write = storage._atomic_write

            def interrupt_csv(path, content):
                if path == store.active_path:
                    raise OSError("simulated interruption before CSV replacement")
                atomic_write(path, content)

            with patch("backend.src.internet_data_getter.sp500.storage._atomic_write", side_effect=interrupt_csv):
                with self.assertRaisesRegex(OSError, "before CSV replacement"):
                    save([(self.jan3, "1271.88"), (self.jan4, "1270.20")])

            pending = json.loads(store.pending_path.read_text(encoding="utf-8"))
            pending["rollback_manifest"]["current"]["observation_count"] += 1
            rollback_bytes = store._manifest_bytes(pending["rollback_manifest"])
            pending["rollback_manifest_sha256"] = storage.sha256(rollback_bytes)
            store.pending_path.write_text(json.dumps(pending, indent=2), encoding="utf-8")
            active_before = store.active_path.read_bytes()
            manifest_before = store.manifest_path.read_bytes()
            pending_before = store.pending_path.read_bytes()

            with self.assertRaisesRegex(ManifestError, "observation count does not match"):
                store.load()

            self.assertEqual(store.active_path.read_bytes(), active_before)
            self.assertEqual(store.manifest_path.read_bytes(), manifest_before)
            self.assertEqual(store.pending_path.read_bytes(), pending_before)

    def test_recovery_preserves_ambiguous_state_when_prior_backup_is_corrupt(self):
        from backend.src.internet_data_getter.sp500 import storage
        from backend.src.internet_data_getter.sp500.storage import StoreError

        def prepare_interrupted_store(store):
            from backend.src.internet_data_getter.sp500.source import Observation

            def save(values):
                page = page_result(self.jan3, self.jan4, values)
                observations = tuple(Observation(day, price) for day, price in values)
                return store.save(observations, (page,), self.now)

            save([(self.jan3, "1271.87")])
            atomic_write = storage._atomic_write

            def interrupt_manifest(path, content):
                if path == store.manifest_path:
                    raise OSError("simulated interruption after CSV replacement")
                atomic_write(path, content)

            with patch("backend.src.internet_data_getter.sp500.storage._atomic_write", side_effect=interrupt_manifest):
                with self.assertRaisesRegex(OSError, "after CSV replacement"):
                    save([(self.jan3, "1271.88"), (self.jan4, "1270.20")])

        def remove_pair(store, pending):
            reference = pending.pop("backup")
            store._resolve_backup(reference["csv_path"]).unlink()
            store._resolve_backup(reference["manifest_path"]).unlink()

        def remove_backup_csv(store, pending):
            store._resolve_backup(pending["backup"]["csv_path"]).unlink()

        def damage_backup_csv(store, pending):
            store._resolve_backup(pending["backup"]["csv_path"]).write_bytes(b"corrupt backup CSV")

        def remove_backup_manifest(store, pending):
            store._resolve_backup(pending["backup"]["manifest_path"]).unlink()

        def damage_backup_manifest(store, pending):
            store._resolve_backup(pending["backup"]["manifest_path"]).write_bytes(b"not JSON")

        def change_backup_digest(_store, pending):
            pending["backup"]["csv_sha256"] = "0" * 64

        def remove_manifest_digest(_store, pending):
            pending["backup"].pop("manifest_sha256")

        def remove_backup_member_and_files(store, pending):
            reference = pending["backup"]
            store._resolve_backup(reference["csv_path"]).unlink()
            store._resolve_backup(reference["manifest_path"]).unlink()
            pending.pop("backup")

        variants = {
            "backup member and files missing": remove_backup_member_and_files,
            "backup CSV missing": remove_backup_csv,
            "backup CSV corrupt": damage_backup_csv,
            "backup manifest missing": remove_backup_manifest,
            "backup manifest corrupt": damage_backup_manifest,
            "backup digest changed": change_backup_digest,
            "backup manifest digest missing": remove_manifest_digest,
        }
        for label, corrupt in variants.items():
            with self.subTest(variant=label), tempfile.TemporaryDirectory() as temp:
                from backend.src.internet_data_getter.sp500.storage import Sp500FileStore

                store = Sp500FileStore(Path(temp) / "data")
                prepare_interrupted_store(store)
                pending = json.loads(store.pending_path.read_text(encoding="utf-8"))
                corrupt(store, pending)
                store.pending_path.write_text(json.dumps(pending, indent=2), encoding="utf-8")
                active_before = store.active_path.read_bytes()
                manifest_before = store.manifest_path.read_bytes()
                with self.assertRaises(StoreError):
                    store.load()
                self.assertTrue(store.pending_path.exists())
                self.assertEqual(store.active_path.read_bytes(), active_before)
                self.assertEqual(store.manifest_path.read_bytes(), manifest_before)

    def test_changed_data_creates_verified_pair_and_restore_uses_it(self):
        self.save([(self.jan3, "1271.87")])
        self.save([(self.jan3, "1271.88"), (self.jan4, "1270.20")])
        manifest = self.store._read_manifest()
        reference = manifest["current"]["previous_versions"][0]
        self.assertTrue((self.store.data_root / reference["csv_path"]).is_file())
        self.assertTrue((self.store.data_root / reference["manifest_path"]).is_file())
        result = self.store.restore(reference["csv_path"], self.now)
        self.assertEqual(result["status"], "updated")
        self.assertEqual([(item.date, item.adjusted_close) for item in self.store.load()], [(self.jan3, "1271.87")])

    def test_tampered_active_csv_is_rejected_before_returning_observations(self):
        from backend.src.internet_data_getter.sp500.storage import ManifestError

        self.save([(self.jan3, "1271.87")])
        self.store.active_path.write_text("date,adjusted_close\n2011-01-03,9999\n", encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "hash does not match"):
            self.store.load()

    def test_restore_rejects_unlisted_and_traversal_paths(self):
        from backend.src.internet_data_getter.sp500.storage import RestoreError

        self.save([(self.jan3, "1271.87")])
        for path in ("backups/sp500/not-listed.csv", "backups/sp500/../../outside.csv"):
            with self.subTest(path=path), self.assertRaises(RestoreError):
                self.store.restore(path, self.now)

    def test_update_recovers_after_csv_replace_but_before_manifest_replace(self):
        from backend.src.internet_data_getter.sp500 import storage

        old = [(self.jan3, "1271.87")]
        new = [(self.jan3, "1271.88"), (self.jan4, "1270.20")]
        self.save(old)
        atomic_write = storage._atomic_write

        def fail_manifest(path, content):
            if path == self.store.manifest_path:
                raise OSError("simulated interruption at manifest commit")
            atomic_write(path, content)

        with patch("backend.src.internet_data_getter.sp500.storage._atomic_write", side_effect=fail_manifest):
            with self.assertRaisesRegex(OSError, "simulated interruption"):
                self.save(new)
        self.assertTrue(self.store.pending_path.exists())
        self.assertEqual(len(self.store.load()), 2)
        self.assertFalse(self.store.pending_path.exists())
        self.assertEqual(self.store._parse_csv(self.store.active_path.read_bytes())[0].adjusted_close, "1271.88")

    def test_update_recovers_before_csv_replace_and_keeps_old_observations(self):
        from backend.src.internet_data_getter.sp500 import storage

        old = [(self.jan3, "1271.87")]
        new = [(self.jan3, "1271.88"), (self.jan4, "1270.20")]
        self.save(old)
        atomic_write = storage._atomic_write

        def fail_csv(path, content):
            if path == self.store.active_path:
                raise OSError("simulated interruption before CSV replacement")
            atomic_write(path, content)

        with patch("backend.src.internet_data_getter.sp500.storage._atomic_write", side_effect=fail_csv):
            with self.assertRaisesRegex(OSError, "before CSV replacement"):
                self.save(new)
        self.assertTrue(self.store.pending_path.exists())
        self.assertEqual(self.store.load(), self.store._parse_csv(self.store.active_path.read_bytes()))
        self.assertEqual(
            [(item.date, item.adjusted_close) for item in self.store.load()],
            [(self.jan3, "1271.87")],
        )
        self.assertFalse(self.store.pending_path.exists())

    def test_initial_save_recovers_after_csv_replacement_without_prior_backup(self):
        from backend.src.internet_data_getter.sp500 import storage
        from backend.src.internet_data_getter.sp500.source import Observation

        values = [(self.jan3, "1271.87")]
        page = page_result(self.jan3, self.jan4, values)
        atomic_write = storage._atomic_write

        def fail_manifest(path, content):
            if path == self.store.manifest_path:
                raise OSError("simulated initial manifest interruption")
            atomic_write(path, content)

        with patch("backend.src.internet_data_getter.sp500.storage._atomic_write", side_effect=fail_manifest):
            with self.assertRaisesRegex(OSError, "initial manifest interruption"):
                self.store.save(tuple(Observation(day, price) for day, price in values), (page,), self.now)
        self.assertEqual(
            [(item.date, item.adjusted_close) for item in self.store.load()], values
        )
        self.assertFalse(self.store.pending_path.exists())

    def test_update_recovers_when_both_new_files_were_replaced_before_journal_cleanup(self):
        from pathlib import Path

        old = [(self.jan3, "1271.87")]
        new = [(self.jan3, "1271.88"), (self.jan4, "1270.20")]
        self.save(old)
        original_unlink = Path.unlink

        def fail_pending_cleanup(path, *args, **kwargs):
            if path == self.store.pending_path:
                raise OSError("simulated interruption before journal cleanup")
            return original_unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", fail_pending_cleanup):
            with self.assertRaisesRegex(OSError, "before journal cleanup"):
                self.save(new)
        self.assertTrue(self.store.pending_path.exists())
        self.assertEqual(
            [(item.date, item.adjusted_close) for item in self.store.load()], new
        )
        self.assertFalse(self.store.pending_path.exists())

    def test_lock_rejects_overlapping_store_operations(self):
        from backend.src.internet_data_getter.sp500.storage import LockError

        with self.store.lock():
            with self.assertRaises(LockError):
                with self.store.lock():
                    pass


if __name__ == "__main__":
    unittest.main()
