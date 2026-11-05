"""HTTP contract tests for portfolio setup routes."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.src.api.main import app
from backend.src.api.model.portfolio_data import PortfolioDataError


class PortfolioRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_indexes_route_returns_the_supported_ordered_indexes(self):
        response = self.client.get("/api/indexes")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [
            {"id": "ibovespa", "name": "IBOVESPA"},
            {"id": "ifix", "name": "IFIX"},
            {"id": "selic", "name": "Selic"},
            {"id": "sp500", "name": "S&P 500"},
        ])

    def test_portfolio_route_returns_series_for_one_two_and_four_indexes(self):
        allocations = [
            [{"index": "ifix", "percentage": 100}],
            [
                {"index": "ibovespa", "percentage": 33.33},
                {"index": "sp500", "percentage": 66.67},
            ],
            [
                {"index": "ibovespa", "percentage": 12.34},
                {"index": "ifix", "percentage": 23.45},
                {"index": "selic", "percentage": 34.56},
                {"index": "sp500", "percentage": 29.65},
            ],
        ]
        for shares in allocations:
            with self.subTest(shares=shares):
                response = self.client.post("/api/portfolio", json={
                    "initial_date": "2020-01-01",
                    "end_date": "2024-12-31",
                    "allocations": shares,
                    "rebalancing": "6_months",
                })

                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.json()), {"series"})
                self.assertEqual(response.json()["series"][0]["name"], "Cumulative portfolio return")

    def test_portfolio_route_returns_inclusive_dates_with_percentage_point_fields(self):
        response = self.client.post("/api/portfolio", json={
            "initial_date": "2011-01-04",
            "end_date": "2011-01-06",
            "allocations": [{"index": "ibovespa", "percentage": 100}],
            "rebalancing": "none",
        })

        self.assertEqual(response.status_code, 200)
        points = response.json()["series"][0]["data"]
        self.assertEqual([point["date"] for point in points], ["2011-01-04", "2011-01-05", "2011-01-06"])
        self.assertEqual(points[0]["x"], 1294099200000)
        self.assertIsInstance(points[0]["x"], int)
        self.assertIsInstance(points[0]["daily_return_pct"], (int, float))
        self.assertAlmostEqual(points[0]["y"], points[0]["cumulative_return_pct"])

    def test_empty_available_date_range_returns_empty_chart_data(self):
        response = self.client.post("/api/portfolio", json={
            "initial_date": "1900-01-01",
            "end_date": "1900-01-02",
            "allocations": [{"index": "selic", "percentage": 100}],
            "rebalancing": "none",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"series": [{
            "name": "Cumulative portfolio return",
            "data": [],
        }]})

    def test_csv_failures_return_clear_unavailable_response(self):
        with patch(
            "backend.src.api.service.portfolio.load_daily_returns",
            side_effect=PortfolioDataError("private CSV path must not appear"),
        ):
            response = self.client.post("/api/portfolio", json=self._valid_payload())

        self.assertEqual(response.status_code, 503)
        self.assertIn("Historical portfolio results are unavailable", response.json()["detail"])
        self.assertNotIn("private CSV path", response.text)

    def test_rejects_missing_or_invalid_dates_and_reversed_range(self):
        payload = self._valid_payload()
        for change in (
            {"initial_date": None},
            {"initial_date": "2024-02-30"},
            {"initial_date": "2020-1-1"},
            {"initial_date": 0},
            {"end_date": "2024-12-31T00:00:00"},
            {"initial_date": "2021-01-01", "end_date": "2020-01-01"},
        ):
            invalid_payload = {**payload, **change}
            with self.subTest(change=change):
                self.assertEqual(
                    self.client.post("/api/portfolio", json=invalid_payload).status_code,
                    422,
                )

    def test_rejects_invalid_allocation_contract(self):
        payload = self._valid_payload()
        invalid_allocations = (
            [],
            [{"index": "ibovespa", "percentage": 99.99}],
            [
                {"index": "ibovespa", "percentage": 50},
                {"index": "ibovespa", "percentage": 50},
            ],
            [
                {"index": "ibovespa", "percentage": 50},
                {"index": "unknown", "percentage": 50},
            ],
            [
                {"index": "ibovespa", "percentage": 50.001},
                {"index": "sp500", "percentage": 49.999},
            ],
            [
                {"index": "ibovespa", "percentage": 100.01},
                {"index": "sp500", "percentage": -0.01},
            ],
        )
        for shares in invalid_allocations:
            with self.subTest(shares=shares):
                response = self.client.post(
                    "/api/portfolio", json={**payload, "allocations": shares}
                )
                self.assertEqual(response.status_code, 422)

    def test_rejects_unknown_extra_fields_and_strategy_values(self):
        payload = self._valid_payload()
        self.assertEqual(
            self.client.post(
                "/api/portfolio", json={**payload, "stored": True}
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.post(
                "/api/portfolio", json={**payload, "rebalancing": "5_years"}
            ).status_code,
            422,
        )

    def test_rejects_raw_json_decimal_precision_and_nonfinite_numbers(self):
        prefix = (
            '{"initial_date":"2020-01-01","end_date":"2024-12-31",'
            '"allocations":[{"index":"ifix","percentage":'
        )
        suffix = '}],"rebalancing":"none"}'
        for token in (
            "99.9999999999999999",
            "100.0000000000000001",
            "100.000",
            "1e309",
            "NaN",
            "Infinity",
        ):
            with self.subTest(token=token):
                response = self.client.post(
                    "/api/portfolio",
                    content=prefix + token + suffix,
                    headers={"content-type": "application/json"},
                )
                self.assertEqual(response.status_code, 422)

    def test_rejects_repeated_json_member_names(self):
        body = (
            '{"initial_date":"2020-01-01","end_date":"2024-12-31",'
            '"allocations":[{"index":"ifix","percentage":50,'
            '"percentage":100}],"rebalancing":"none"}'
        )

        response = self.client.post(
            "/api/portfolio",
            content=body,
            headers={"content-type": "application/json"},
        )

        self.assertEqual(response.status_code, 422)

    def test_exact_json_validation_also_covers_missing_and_empty_content_type(self):
        invalid_bodies = (
            (
                "overprecision",
                '{"initial_date":"2020-01-01","end_date":"2024-12-31",'
                '"allocations":[{"index":"ifix","percentage":99.9999999999999999}],'
                '"rebalancing":"none"}',
            ),
            (
                "nonfinite",
                '{"initial_date":"2020-01-01","end_date":"2024-12-31",'
                '"allocations":[{"index":"ifix","percentage":NaN}],'
                '"rebalancing":"none"}',
            ),
            (
                "duplicate member",
                '{"initial_date":"2020-01-01","end_date":"2024-12-31",'
                '"allocations":[{"index":"ifix","percentage":50,"percentage":100}],'
                '"rebalancing":"none"}',
            ),
        )

        for content_type in (None, ""):
            for case_name, body in invalid_bodies:
                with self.subTest(content_type=content_type, case=case_name):
                    headers = {} if content_type is None else {"content-type": content_type}
                    response = self.client.post("/api/portfolio", content=body, headers=headers)

                    self.assertEqual(response.status_code, 422)
                    self.assertEqual(response.json()["detail"], "The JSON body contains invalid or repeated values.")

    def test_accepts_valid_json_when_content_type_is_missing_or_empty(self):
        body = (
            '{"initial_date":"2020-01-01","end_date":"2024-12-31",'
            '"allocations":[{"index":"ifix","percentage":100}],'
            '"rebalancing":"none"}'
        )

        for headers in ({}, {"content-type": ""}):
            with self.subTest(headers=headers):
                response = self.client.post("/api/portfolio", content=body, headers=headers)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.json()), {"series"})

    def test_json_suffix_media_type_keeps_exact_validation(self):
        prefix = (
            '{"initial_date":"2020-01-01","end_date":"2024-12-31",'
            '"allocations":[{"index":"ifix","percentage":'
        )
        suffix = '}],"rebalancing":"none"}'

        valid = self.client.post(
            "/api/portfolio",
            content=prefix + "100" + suffix,
            headers={"content-type": "application/vnd.portfolio+json"},
        )
        invalid = self.client.post(
            "/api/portfolio",
            content=prefix + "99.9999999999999999" + suffix,
            headers={"content-type": "application/vnd.portfolio+json"},
        )

        self.assertEqual(valid.status_code, 200)
        self.assertEqual(set(valid.json()), {"series"})
        self.assertEqual(invalid.status_code, 422)

    def test_lone_surrogate_validation_error_is_serialized_as_422(self):
        body = (
            '{"initial_date":"\\ud800","end_date":"2024-12-31",'
            '"allocations":[{"index":"ifix","percentage":100}],'
            '"rebalancing":"none"}'
        )

        response = self.client.post(
            "/api/portfolio",
            content=body,
            headers={"content-type": "application/json"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"detail": "The request contains invalid or missing fields."})

    def test_rejects_parser_depth_errors_with_serializable_422(self):
        body = '{"unexpected":' + ("[" * 1500) + "0" + ("]" * 1500) + "}"

        response = self.client.post(
            "/api/portfolio",
            content=body,
            headers={"content-type": "application/json"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json()["detail"], str)

    def test_rejects_non_json_media_type_instead_of_using_a_fallback_decoder(self):
        response = self.client.post(
            "/api/portfolio",
            content=(
                '{"initial_date":"2020-01-01","end_date":"2024-12-31",'
                '"allocations":[{"index":"ifix","percentage":'
                '99.9999999999999999}],"rebalancing":"none"}'
            ),
            headers={"content-type": "text/plain"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIsNotNone(response.json())

    def test_openapi_retains_the_portfolio_request_body_schema(self):
        openapi = self.client.get("/openapi.json").json()
        request_body = openapi["paths"]["/api/portfolio"]["post"]["requestBody"]
        schema_ref = request_body["content"]["application/json"]["schema"]["$ref"]
        request_schema = openapi["components"]["schemas"][schema_ref.rsplit("/", 1)[1]]

        self.assertTrue(schema_ref.endswith("/PortfolioConfiguration"))
        self.assertEqual(
            set(request_schema["properties"]),
            {"initial_date", "end_date", "allocations", "rebalancing"},
        )

    @staticmethod
    def _valid_payload():
        return {
            "initial_date": "2020-01-01",
            "end_date": "2024-12-31",
            "allocations": [
                {"index": "ibovespa", "percentage": 40},
                {"index": "sp500", "percentage": 60},
            ],
            "rebalancing": "none",
        }


if __name__ == "__main__":
    unittest.main()
