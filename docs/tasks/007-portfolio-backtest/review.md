# Independent review — 2026-11-05 (America/Sao_Paulo)

Verdict: **changes required**. Specification s001 (`290c59a4ab8d92edbe1d4a3fe946468d04f46a80328bb61d2508d8e716a1ab45`), plan p001 (`88b763d439120a32f0ad01810fb7fae37cb4075e687339b99ddf9a1decff2e98`), snapshot `7a8ff805db78041bad3ca739ae95ba8a9ec5a8e0:sha256:d492e6c312246aabc65494200edccee888bab631b8ec0ac198af42d24cdf2973`. The snapshot command after review returned the same identity. The reviewer inspected the tracked diff, new untracked implementation/tests, approved specification, plan and developer evidence. No production code or tests were edited during review.

## Findings

### PB-R01 — HTTP surrogate regression asserts the wrong error path (P2, AC-006/AC-007)

`backend/src/api/tests/test_portfolio.py:260-274` sends an `initial_date` containing a lone surrogate and expects the generic Pydantic request-validation error. The request schema accepts this value as a string; `_parse_date` in `backend/src/api/service/portfolio.py:26-28` then raises `PortfolioConfigurationError`, whose handler returns `initial_date must be a YYYY-MM-DD string`. An independent direct call using the same `PortfolioConfiguration` confirmed that exact service exception and message. Consequently the asserted HTTP body cannot match when the route suite can run. The test also does not exercise PC-R08's Pydantic validation error containing an unencodable input, so it does not establish the intended regression. Route execution is blocked by missing FastAPI/httpx; the conclusion about HTTP mapping follows inspection of `main.py:15-25`, not a TestClient run. Add a regression that actually triggers the Pydantic error and verify both paths with the real route when dependencies are available.

### PB-R02 — CSV selection occurs after whole-file numeric validation and outside pandas (P2, AC-001/AC-006)

`backend/src/api/model/portfolio_data.py:55-72` converts every asset value across the full table before filtering through a Python list comprehension. A local illustrative CSV with an invalid numeric value on 2024-01-01 and a valid row on the requested 2024-01-02 raised `PortfolioDataError`, despite s001's explicit selected-row value validation. The same code filters with Python rather than pandas, contrary to the user request and AC-001. Apply the inclusive date selection in pandas and validate numeric values for the selected rows, while retaining the specified complete-table schema/date integrity checks. The reproduction ran through `backend/.venv` with pandas 3.0.1, which is outside the declared supported range.

### PB-R03 — Malformed date/timestamp response reaches the chart (P2, AC-004/AC-005)

`frontend/src/services/portfolio.ts:65-76` checks only the date's text pattern and whether `x` is a safe integer. It accepts impossible calendar dates and timestamps unrelated to the `date` field. With Axios mocked locally, an independent call to `submitPortfolio` accepted `{x: 0, y: 1, date: "2024-99-99", daily_return_pct: 1, cumulative_return_pct: 1}`. The UI therefore treats a malformed server response as a valid result, showing an impossible summary date and a 1970 chart point instead of an error. Reject invalid dates, non-midnight/mismatched timestamps and invalid chronological ordering as appropriate without altering the returned series; add regression coverage.

### PB-R04 — Behavioral test-first evidence for calculations is missing (P2 process blocker, AC-007)

`verification.md:14` records that the model/calculation tests' only pre-implementation run failed because the new module did not exist. That is a setup/import failure, not an observed behavioral red. Their later 13 passing cases demonstrate the implemented behavior but cannot establish that those assertions were observed failing before the calculation and model implementation. The separate old acknowledgement response red and frontend reds are meaningful but do not cover the calculation/model behaviors. Preserve the record; do not reconstruct an unobserved prior red or claim this requirement passed. The lead/user must decide how to address this evidence gap.

## Independent checks and limits

- Ran `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio_calculation backend.src.api.tests.test_portfolio_result_contract -v`: 14 passed, using pandas 3.0.1 outside the project's `<3` constraint.
- Ran `pnpm test` in `frontend`: 28 tests passed.
- Ran local, read-only illustrative reproductions for PB-R01 (service error path), PB-R02 (out-of-range invalid row), and PB-R03 (mocked Axios malformed point). No network requests were made.
- FastAPI/httpx are absent in the available offline backend environment. The HTTP suite and supported-version backend checks were not run. No browser QA was performed as part of review; independent QA remains required. Numerical review found no additional calculation defect in the inspected routine, but these limits prevent a full contract pass.
