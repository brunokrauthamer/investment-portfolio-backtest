# Round 2 backend regression tests — red

With the round 1 API implementation unchanged, `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_rejects_raw_json_decimal_precision_and_nonfinite_numbers backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_rejects_repeated_json_member_names backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_openapi_retains_the_portfolio_request_body_schema -v` produced these failures:

- **PC-R03:** Raw JSON `99.9999999999999999`, `100.0000000000000001` and `100.000` returned 200 instead of 422; `1e309`, `NaN` and `Infinity` returned 500 instead of 422.
- **PC-R04:** A repeated `percentage` JSON member returned 200 instead of 422.

The OpenAPI request body schema regression passed before repair and is retained to ensure strict raw-body decoding does not remove the typed request contract.
