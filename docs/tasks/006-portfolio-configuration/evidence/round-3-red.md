# Initial round 3 regression evidence — red

Approved input: specification `s001` (`1ba23e8edeaf05f02a39fa7e7a95ee9a2ad05ba7be1178d355a29a67a8aabd3f`), plan `p001` (`106e4271058d71e3ce78f5c8466b0eda50a1c0ec60d867b6eec0d469191bda8e`), review input snapshot `d9f0c83c824cdbcd8d765c19735be400974798b5:sha256:a84d04250e48ad8f658169eab04c74c84fe8206fe7880a85460c0f09cfa3b862`.

Before changing the route, ran:

```text
backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_exact_json_validation_also_covers_missing_and_empty_content_type backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_rejects_parser_depth_errors_with_serializable_422 backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_rejects_non_json_media_type_instead_of_using_a_fallback_decoder -v
```

Observed seven behavioral failures. The overprecision and duplicate-member requests received HTTP 200 and nonfinite `NaN` received HTTP 500 with both missing and empty `Content-Type`. The deeply nested invalid JSON body with explicit `application/json` received HTTP 500 rather than a serializable HTTP 422. These reproduce PC-R06 and PC-R07. The auxiliary non-JSON media-type case already returned HTTP 422 and passed before the repair; this confirms that path did not have the same acknowledgement bypass.

The valid missing/empty `Content-Type` compatibility regression was added after this red run; it verifies the existing accepted behavior should remain HTTP 200 with `{"status":"ok"}`.
