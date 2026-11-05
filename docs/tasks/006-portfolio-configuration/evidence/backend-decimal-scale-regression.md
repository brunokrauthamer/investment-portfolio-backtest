# Round 2 decimal scale regression

The review's raw HTTP evidence also showed `100.000` being acknowledged with HTTP 200. After the first exact-decimal decoder was added, `PortfolioRouteTests.test_rejects_raw_json_decimal_precision_and_nonfinite_numbers` was extended with that token and failed: the response remained 200 because `Decimal("100.000")` is numerically equal to 100 even though the JSON number spells three decimal places.

The raw decimal decoder now rejects a decimal exponent below -2 before Pydantic sees the value. The same regression test passes and the API returns HTTP 422 for `100.000`.
