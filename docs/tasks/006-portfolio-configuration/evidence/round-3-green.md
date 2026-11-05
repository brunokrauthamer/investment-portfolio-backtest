# Initial round 3 regression evidence — green

Input: approved spec `s001` and plan `p001`; round 3 input snapshot `d9f0c83c824cdbcd8d765c19735be400974798b5:sha256:a84d04250e48ad8f658169eab04c74c84fe8206fe7880a85460c0f09cfa3b862`.

## Focused regressions

After repairing `ExactJsonRoute`, ran:

```text
backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_exact_json_validation_also_covers_missing_and_empty_content_type backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_accepts_valid_json_when_content_type_is_missing_or_empty backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_rejects_parser_depth_errors_with_serializable_422 backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_rejects_non_json_media_type_instead_of_using_a_fallback_decoder backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_rejects_raw_json_decimal_precision_and_nonfinite_numbers backend.src.api.tests.test_portfolio.PortfolioRouteTests.test_rejects_repeated_json_member_names -v
```

All six focused test methods passed. Missing and empty `Content-Type` now use the exact decoder: invalid overprecision, `NaN` and duplicate members return HTTP 422, while valid JSON remains HTTP 200 with `{"status":"ok"}`. Explicit `application/json` parser depth errors return HTTP 422 with a JSON-serializable string detail. Unsupported `text/plain` is rejected with HTTP 422. Existing explicit JSON and duplicate-member regressions remain green.

## Related checks

- `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio backend.src.api.tests.test_health -v`: 15 tests passed.
- `pnpm test` from `frontend`: 22 tests passed across five files.
- `pnpm typecheck` from `frontend`: passed.
- `pnpm build` from `frontend`: passed. Vite emitted the existing large-chunk warning (864.02 kB minified JavaScript); no build error.
- `backend/.venv/Scripts/python.exe -m pip check`: passed; no broken requirements.
- `backend/.venv/Scripts/python.exe -m compileall -q backend/src/api`: passed.
- `git diff --check`: passed; Git reported only LF-to-CRLF working-copy notices.
