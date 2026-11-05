"""Calculation tests use explicitly illustrative returns, never market history."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from backend.src.api.model.portfolio_data import (
    DailyReturnObservation,
    PortfolioDataError,
    load_daily_returns,
)
from backend.src.api.service.portfolio import (
    PortfolioCalculationError,
    calculate_portfolio_series,
)


def row(day: str, **returns: float):
    values = {name: 0.0 for name in ("ibovespa", "ifix", "selic", "sp500")}
    values.update(returns)
    return DailyReturnObservation(date=date.fromisoformat(day), returns=values)


class PortfolioCalculationTests(unittest.TestCase):
    def calculate(self, rows, allocations, rebalancing="none"):
        return calculate_portfolio_series(rows, allocations, rebalancing)["series"][0]["data"]

    def test_includes_first_daily_return_and_compounds_without_intermediate_rounding(self):
        points = self.calculate(
            [
                row("2011-01-04", ibovespa=0.01),
                row("2011-01-05"),
                row("2011-01-06", ibovespa=0.01),
            ],
            [{"index": "ibovespa", "percentage": 100}],
        )

        self.assertEqual([point["x"] for point in points], [
            1294099200000, 1294185600000, 1294272000000,
        ])
        self.assertEqual([point["daily_return_pct"] for point in points], [1.0, 0.0, 1.0])
        for point, expected in zip(points, [1.0, 1.0, 2.01]):
            self.assertAlmostEqual(point["cumulative_return_pct"], expected)
            self.assertEqual(point["y"], point["cumulative_return_pct"])
        self.assertEqual([point["date"] for point in points], [
            "2011-01-04", "2011-01-05", "2011-01-06",
        ])

    def test_uses_start_of_day_weights_then_drifts_by_relative_performance(self):
        points = self.calculate(
            [
                row("2024-01-02", ibovespa=1.0),
                row("2024-01-03", ifix=1.0),
            ],
            [
                {"index": "ibovespa", "percentage": 50},
                {"index": "ifix", "percentage": 50},
            ],
        )

        self.assertEqual(points[0]["daily_return_pct"], 50.0)
        self.assertAlmostEqual(points[1]["daily_return_pct"], 100 / 3)
        self.assertAlmostEqual(points[1]["cumulative_return_pct"], 100.0)

    def test_rebalances_repeatedly_after_the_anniversary_row_return(self):
        points = self.calculate(
            [
                row("2024-01-31", ibovespa=0.5),
                row("2024-04-30"),
                row("2024-05-01", ifix=1.0),
                row("2024-07-31", ifix=0.5),
                row("2024-08-01", ifix=1.0),
            ],
            [
                {"index": "ibovespa", "percentage": 75},
                {"index": "ifix", "percentage": 25},
            ],
            "3_months",
        )

        self.assertEqual([point["daily_return_pct"] for point in points], [37.5, 0.0, 25.0, 20.0, 25.0])

    def test_each_calendar_strategy_uses_its_configured_interval(self):
        anniversary_dates = {
            "3_months": "2024-04-30",
            "6_months": "2024-07-31",
            "1_year": "2025-01-31",
            "2_years": "2026-01-31",
            "3_years": "2027-01-31",
        }
        for strategy, anniversary in anniversary_dates.items():
            with self.subTest(strategy=strategy):
                following_date = (date.fromisoformat(anniversary) + timedelta(days=1)).isoformat()
                points = self.calculate(
                    [
                        row("2024-01-31", ibovespa=0.5),
                        row(anniversary),
                        row(following_date, ifix=1.0),
                    ],
                    [
                        {"index": "ibovespa", "percentage": 75},
                        {"index": "ifix", "percentage": 25},
                    ],
                    strategy,
                )

                self.assertEqual(points[-1]["daily_return_pct"], 25.0)

    def test_missing_anniversary_uses_first_later_row_then_resets_for_following_row(self):
        points = self.calculate(
            [
                row("2024-01-31", ibovespa=0.5),
                row("2024-05-02", ifix=1.0),
                row("2024-05-03", ifix=1.0),
            ],
            [
                {"index": "ibovespa", "percentage": 75},
                {"index": "ifix", "percentage": 25},
            ],
            "3_months",
        )

        self.assertAlmostEqual(points[1]["daily_return_pct"], 200 / 11)
        self.assertEqual(points[2]["daily_return_pct"], 25.0)

    def test_gap_spanning_multiple_anniversaries_resets_once_after_first_later_row(self):
        points = self.calculate(
            [
                row("2024-01-31", ibovespa=0.5),
                row("2024-08-01"),
                row("2024-08-02", ifix=1.0),
            ],
            [
                {"index": "ibovespa", "percentage": 75},
                {"index": "ifix", "percentage": 25},
            ],
            "3_months",
        )

        self.assertEqual(points[2]["daily_return_pct"], 25.0)

    def test_month_end_and_leap_day_anniversaries_clamp_from_original_anchor(self):
        month_end_points = self.calculate(
            [
                row("2024-01-31", ibovespa=0.5),
                row("2024-04-29"),
                row("2024-04-30"),
                row("2024-05-01", ifix=1.0),
            ],
            [
                {"index": "ibovespa", "percentage": 75},
                {"index": "ifix", "percentage": 25},
            ],
            "3_months",
        )
        leap_points = self.calculate(
            [
                row("2024-02-29", ibovespa=0.5),
                row("2025-02-27"),
                row("2025-02-28"),
                row("2025-03-01", ifix=1.0),
            ],
            [
                {"index": "ibovespa", "percentage": 75},
                {"index": "ifix", "percentage": 25},
            ],
            "1_year",
        )

        self.assertEqual(month_end_points[1]["daily_return_pct"], 0.0)
        self.assertEqual(month_end_points[3]["daily_return_pct"], 25.0)
        self.assertEqual(leap_points[1]["daily_return_pct"], 0.0)
        self.assertEqual(leap_points[3]["daily_return_pct"], 25.0)

    def test_selic_is_compounded_and_csv_zero_returns_are_used(self):
        points = self.calculate(
            [row("2024-01-02", selic=0.01), row("2024-01-03", selic=0.01)],
            [{"index": "selic", "percentage": 100}],
        )

        self.assertEqual(points[0]["daily_return_pct"], 1.0)
        self.assertEqual(points[1]["daily_return_pct"], 1.0)
        self.assertAlmostEqual(points[1]["cumulative_return_pct"], 2.01)

    def test_empty_range_returns_no_points(self):
        response = calculate_portfolio_series(
            [], [{"index": "selic", "percentage": 100}], "none",
        )

        self.assertEqual(response, {
            "series": [{"name": "Cumulative portfolio return", "data": []}],
        })

    def test_rejects_a_total_loss_because_weights_cannot_drift_after_it(self):
        with self.assertRaises(PortfolioCalculationError):
            self.calculate(
                [row("2024-01-02", ibovespa=-1.0)],
                [{"index": "ibovespa", "percentage": 100}],
            )


class PortfolioDataModelTests(unittest.TestCase):
    def write_csv(self, contents: str) -> Path:
        temporary = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", delete=False)
        temporary.write(contents)
        temporary.close()
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        return Path(temporary.name)

    def test_reads_and_filters_inclusively_preserving_dates_and_zero_observations(self):
        path = self.write_csv(
            "date,ibovespa,ifix,selic,sp500\n"
            "2024-01-01,0,0,0,0\n"
            "2024-01-02,0.01,0,0.0001,0\n"
            "2024-01-03,0,0,0.0001,0.02\n"
        )

        result = load_daily_returns(date(2024, 1, 2), date(2024, 1, 3), path)

        self.assertEqual([observation.date.isoformat() for observation in result], ["2024-01-02", "2024-01-03"])
        self.assertEqual(result[0].returns["ifix"], 0.0)
        self.assertEqual(result[0].returns["selic"], 0.0001)

    def test_does_not_validate_asset_values_outside_the_requested_rows(self):
        path = self.write_csv(
            "date,ibovespa,ifix,selic,sp500\n"
            "2024-01-01,not-a-number,0,0,0\n"
            "2024-01-02,0.01,0,0,0\n"
        )

        result = load_daily_returns(date(2024, 1, 2), date(2024, 1, 2), path)

        self.assertEqual([observation.date for observation in result], [date(2024, 1, 2)])
        self.assertEqual(result[0].returns["ibovespa"], 0.01)

    def test_rejects_duplicate_or_unsorted_dates_and_invalid_values(self):
        invalid_csvs = (
            "date,ibovespa,ifix,selic,sp500\n2024-01-01,0,0,0,0\n2024-01-01,0,0,0,0\n",
            "date,ibovespa,ifix,selic,sp500\n2024-01-02,0,0,0,0\n2024-01-01,0,0,0,0\n",
            "date,ibovespa,ifix,selic,sp500\n2024-01-01,NaN,0,0,0\n",
            "date,ibovespa,ifix,selic,sp500\n2024-01-01,-1.01,0,0,0\n",
        )
        for content in invalid_csvs:
            with self.subTest(content=content):
                with self.assertRaises(PortfolioDataError):
                    load_daily_returns(date(2024, 1, 1), date(2024, 1, 3), self.write_csv(content))

    def test_missing_data_file_fails_instead_of_returning_an_empty_range(self):
        with self.assertRaises(PortfolioDataError):
            load_daily_returns(date(2024, 1, 1), date(2024, 1, 3), Path("missing-file.csv"))


if __name__ == "__main__":
    unittest.main()
