"""Regression test for the chart-ready portfolio result contract."""

import unittest

from backend.src.api.model.portfolio import PortfolioConfiguration
from backend.src.api.service.portfolio import calculate_portfolio


class PortfolioResultContractTests(unittest.TestCase):
    def test_valid_request_returns_chart_ready_series_instead_of_acknowledgement(self):
        result = calculate_portfolio(PortfolioConfiguration(
            initial_date="2011-01-04",
            end_date="2011-01-06",
            allocations=[{"index": "ibovespa", "percentage": 100}],
            rebalancing="none",
        ))

        self.assertEqual(set(result), {"series"})
        self.assertEqual(result["series"][0]["name"], "Cumulative portfolio return")
        self.assertEqual(
            set(result["series"][0]["data"][0]),
            {"x", "y", "date", "daily_return_pct", "cumulative_return_pct"},
        )
        self.assertEqual(
            [point["date"] for point in result["series"][0]["data"]],
            ["2011-01-04", "2011-01-05", "2011-01-06"],
        )


if __name__ == "__main__":
    unittest.main()
