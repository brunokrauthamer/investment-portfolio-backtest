# Verification — implementation pass 1

Spec s001 (`290c59a4ab8d92edbe1d4a3fe946468d04f46a80328bb61d2508d8e716a1ab45`), plan p001 (`88b763d439120a32f0ad01810fb7fae37cb4075e687339b99ddf9a1decff2e98`). Implementation snapshot: `evidence/implementation-snapshot.json`.

## Environment and limitations

- Frontend: pnpm 11.25.0, Node runtime supplied by Codex. Dependencies were installed offline from a copied local pnpm content store; 143 packages reused and zero downloaded. The temporary copied store was removed after checks. Frontend `node_modules` remains ignored local tooling.
- Backend: `backend/.venv` uses the bundled Python 3.12.14 runtime with locally available system packages pandas 3.0.1 and pydantic 2.14.1. These allowed model/service checks but pandas 3.0.1 is outside the supported `backend/requirements.txt` range (`<3`).
- A supported backend environment could not be assembled offline: the system Python 3.9 pip wheel cache was empty, no neighboring worktree contained a backend environment, and `python -m pip install --no-index -r backend/requirements.txt` failed because FastAPI was not cached. FastAPI and httpx are unavailable, so API TestClient and HTTP handling tests could not run. The browser was not assessed by the developer; independent QA must exercise it when available.

## Test-first evidence

- Backend response regression: added `test_valid_request_returns_chart_ready_series_instead_of_acknowledgement` before changing the service. `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio_result_contract -v` failed on the old service because it returned `status` where the test expected `series`. After implementation, the same test passed (1 test).
- Backend model/calculation suite was authored before implementation. Its first attempted run, `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio_calculation -v`, could not import the not-yet-created `portfolio_data` module. After model/service implementation and correction of test-fixture construction and floating-point assertions, all 13 tests passed. This is a module-availability red followed by green evidence; detailed formula assertions were not run against an earlier calculation implementation.
- Frontend backtest tests were added before the page/service changes. `pnpm test -- src/pages/ExampleChart/backtest.test.tsx` observed 5 failures against the old page: the fictional chart rendered before calculation and the expected calculate action, result/empty/error states were absent. After implementation, `pnpm exec vitest run src/pages/ExampleChart/backtest.test.tsx` passed all 5 tests. The expanded suite now also rejects malformed responses.

## Integrated checks

| Check | Result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio_calculation backend.src.api.tests.test_portfolio_result_contract -v` | Passed: 14 tests. Covers first-day return and compounding, start-of-day weights and drift, all calendar intervals, repeated and skipped anniversaries, month-end/leap-day clamping, gaps spanning anniversaries, Selic/zero returns, empty ranges, invalid/lost portfolio cases, CSV validation/filtering and chart shape. Run with the unsupported pandas 3.0.1 partial environment noted above. |
| `pnpm test` | Passed: 28 tests across 6 files. |
| `pnpm typecheck` | Passed. |
| `pnpm build` | Passed. Vite reported the existing ApexCharts bundle exceeds 500 kB after minification. |
| `backend/.venv/Scripts/python.exe -m py_compile ...` on changed backend sources/tests | Passed syntax compilation. |
| `git diff --check` | Passed; Git reported only configured LF-to-CRLF conversion warnings. |
| `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_health backend.src.api.tests.test_portfolio -v` | Blocked before execution: both test modules fail to import `fastapi.testclient` (`ModuleNotFoundError: No module named 'fastapi'`). |

## QA handoff

HTTP route behavior, safe 503 translation, malformed lone-surrogate 422 handling and user-facing browser behavior remain unverified here. The route and browser tests are present for independent QA. The developer made no network requests, did not modify normalized source data and did not issue an independent review or QA verdict.

## Post-review fix pass 1

Input: independent review findings PB-R01–PB-R04 against s001/p001 and implementation snapshot `d492e6c312246aabc65494200edccee888bab631b8ec0ac198af42d24cdf2973`.

- **PB-R02 — selected-row numeric validation (fixed):** Added `test_does_not_validate_asset_values_outside_the_requested_rows` before the model change. Red command: `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio_calculation.PortfolioDataModelTests.test_does_not_validate_asset_values_outside_the_requested_rows -v`. It errored because pandas attempted to convert out-of-range `not-a-number` at row 0. The model now builds an inclusive pandas date mask before converting asset values, while still validating the complete date sequence/schema. The same command passed (1 test). Full calculation/model and result contract run passed 15 tests.
- **PB-R03 — response point date/timestamp/order validation (fixed):** Added `src/services/portfolio.test.ts` before the validator change. Red command: `pnpm exec vitest run src/services/portfolio.test.ts`. It failed because the service accepted `2024-99-99` with `x: 0`. The service now checks Gregorian calendar dates, verifies each `x` equals that date's UTC-midnight epoch milliseconds, and rejects repeated or out-of-order points. It returns the original series unchanged. The focused suite then passed 2 tests (invalid dates/timestamps/order and series identity).
- **PB-R01 — route error regression (blocked):** The current test sends a surrogate in `initial_date`; that string passes the Pydantic request schema and follows the service's `PortfolioConfigurationError` path, so the expected generic Pydantic error body is incorrect. An accurate PC-R08 case should put the surrogate in `rebalancing` (a `Literal` field), provoking Pydantic `RequestValidationError`. FastAPI/httpx remain unavailable locally, so the HTTP red cannot be observed; the route test was not changed and no fix is claimed. QA needs a supported backend environment and must verify both request-error paths over the actual route.
- **PB-R04 — test-first history gap preserved:** The earlier calculation/model assertions were not observed failing behaviorally before their implementation. No retrospective red was created or claimed. This evidence gap remains open for QA/lead disposition.

Post-fix checks:

| Check | Result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio_calculation backend.src.api.tests.test_portfolio_result_contract -v` | Passed: 15 tests with bundled Python 3.12.14, pandas 3.0.1 (still outside manifest `<3`). |
| `pnpm test` | Passed: 30 tests across 7 files. |
| `pnpm typecheck` | Passed. |
| `pnpm build` | Passed; Vite's ApexCharts bundle-size warning remains. |
| `backend/.venv/Scripts/python.exe -m py_compile ...` for changed model/test files | Passed. |
| `git diff --check` | Passed with only LF-to-CRLF configuration notices. |
| HTTP/TestClient tests | Still blocked because FastAPI/httpx are unavailable offline. |

The updated code snapshot is recorded in `evidence/post-review-fix-snapshot.json`. Browser QA remains outstanding.

## QA paused at user request — 2026-11-05 (America/Sao_Paulo)

The user asked for testing to stop until the frontend is ready. The independent QA assignment was interrupted before browser verification and did not return an acceptance assessment. QA and browser behavior are incomplete; no QA pass is recorded. Resume QA only when the user signals readiness, and first identify the then-current implementation snapshot.

PB-R02 and PB-R03 have developer fix evidence but remain pending independent QA. PB-R01 remains blocked and unfixed, and PB-R04 remains an open test-first evidence gap. FastAPI/httpx were unavailable offline, and the backend checks above used pandas 3.0.1 outside the declared supported range. The previous implementation, review and fix evidence remains unchanged.
