# Verification — specification s001, plan p001

## Developer TDD evidence

- **Backend routes, AC-001 and AC-004:** Before adding `portfolio_router`, `backend/src/api/tests/test_portfolio.py` failed with 14 assertions across five tests. Both valid paths returned 404; valid requests expected 200 and invalid requests expected 422. The route and contract were added; the portfolio and health suites passed all seven tests. Evidence: `evidence/backend-tdd-red.md`, `evidence/backend-tdd-green.txt`.
- **Frontend form, AC-001 through AC-005:** Tests were added to `frontend/src/pages/ExampleChart/index.test.tsx` before the form. Eight new tests failed against the chart-only page because its expected form, loading errors, date feedback and submit behavior did not exist; the original chart test passed. The form and service were implemented; all 18 tests across the frontend suite passed. Evidence: `evidence/frontend-tdd-red.txt`, `evidence/frontend-green.txt`.
- **Percentage input regression, AC-002 and AC-004:** A valid decimal field initially made `HTMLFormElement.checkValidity()` false because the input pattern had an extra backslash. The focused equal-date submission test reproduced `expected false to be true`. After correcting the pattern, the focused test passed and the integrated suite passed. Evidence: `evidence/frontend-pattern-regression.md`.
- **Strict ISO date regression, AC-003 and AC-004:** Before date-specific validation, the API acknowledged integer `0` and datetime `2024-12-31T00:00:00` as dates (HTTP 200 instead of 422). A regression test reproduced both. After requiring a string in `YYYY-MM-DD` form and parsing a real date, all five portfolio tests passed. Evidence: `evidence/backend-date-validation-regression.md`, `evidence/backend-date-regression-green.txt`.

## Current implementation checks

- `pnpm install --frozen-lockfile` in `frontend`: passed; lockfile is current with Axios.
- `pnpm test` in `frontend`: passed, 5 test files and 18 tests (`evidence/frontend-green.txt`). This includes existing chart coverage.
- `pnpm typecheck` in `frontend`: passed (`evidence/frontend-typecheck-build.txt`).
- `pnpm build` in `frontend`: passed (`evidence/frontend-typecheck-build.txt`). Vite reports the existing chart bundle above 500 kB; this is a warning, not a build failure.
- `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio backend.src.api.tests.test_health -v`: passed, 7 tests (`evidence/backend-tdd-green.txt`). The HTTP contract suite covers exact index output, valid one/two/four index requests, bad dates, invalid or duplicate allocations, unknown fields and strategies. Health still passes.
- `backend/.venv/Scripts/python.exe -m pip check`: passed with no broken requirements (`evidence/backend-pip-check.txt`).
- `backend/.venv/Scripts/python.exe -m compileall -q backend/src/api`: passed.
- `git diff --check`: passed; Git emitted only its existing LF-to-CRLF working-copy notices.

## Criteria status from implementation checks

| Criterion | Developer evidence | Independent review / QA |
| --- | --- | --- |
| AC-001 — Index route and load | Exact API contract, Axios load, malformed-response rejection and retry UI tests pass. | Pending review and browser QA. |
| AC-002 — Allocations | Equal default; selection down to one/two; zero values; exact total; locks and a four-index decimal mix tested. | Pending review and browser QA. |
| AC-003 — Dates and strategy | Missing, reversed and equal dates plus all six strategy values tested. | Pending review and browser QA. |
| AC-004 — Submission | Request shape, acknowledgement, retry and backend rejection tests pass. | Pending review and browser QA. |
| AC-005 — Integrated presentation | Page styles and chart disclosure retained; frontend build passes. | 1280 px and 768 px development/preview browser checks pending. |
| AC-006 — Boundaries and usage | Health regression passes; acquisition/domain/data code untouched; dependencies and API/proxy usage documented. | Pending independent review. |

## Integrated run for review and QA

From the repository root, start the backend using `backend/README.md`. In `frontend`, run `pnpm dev --host 127.0.0.1` and open the reported URL. For the built frontend, run `pnpm build` then `pnpm preview --host 127.0.0.1 --port 4173 --strictPort`. Both Vite processes proxy `/api` to the local FastAPI server. A production deployment must provide an equivalent same-origin proxy.

The developer did not perform independent browser QA. QA must exercise the integrated development and preview sites with the running API, including allocation interaction and totals, valid and rejected submissions, load/error retry, chart disclosure and widths of 1280 px and 768 px. Record actual browser actions, observations and the evaluated snapshot before any final approval request.

## Developer repair evidence — initial round 2

The independent review reproduction prompted test-first fixes for all five findings; their initial open statuses remain for the reviewer to disposition:

- **PC-R01 — settled values:** Added a UI regression that enters 40% IBOVESPA, blurs, then enters 50% IFIX and blurs. Before repair the IBOVESPA field remained 40 although its committed share was 25. The form now preserves only the active text draft; every settled field renders the current committed share. See `evidence/round-2-frontend-red.md` and `evidence/round-2-frontend-green.md`.
- **PC-R02 — invalid draft submission:** Added a form submission regression with dates filled and a focused 101% IFIX draft. Before repair Axios submitted the previous valid allocation. The form now blocks submit when the active draft cannot be parsed or does not match its committed share; blur visibly restores the committed value. See the same frontend red/green evidence.
- **PC-R03 — raw decimal precision and nonfinite tokens:** Added raw HTTP JSON cases for both precision boundary tokens, `1e309`, `NaN` and `Infinity`. Before repair the precision cases returned 200 and the out-of-range/nonfinite cases returned 500. The route now decodes decimal tokens as `Decimal` before Pydantic validation and rejects nonfinite constants as 422. See `evidence/round-2-backend-red.md` and `evidence/round-2-backend-green.md`.
- **PC-R03 — decimal scale:** A follow-up regression added the raw JSON token `100.000`; after exact decoding but before the scale check it still returned 200. The decoder now rejects more than two fractional places. See `evidence/backend-decimal-scale-regression.md`.
- **PC-R04 — repeated JSON members:** Added a raw body with two `percentage` members. It returned 200 before repair and returns 422 after adding duplicate-member detection in the portfolio API route. The route retains its typed request model; an OpenAPI regression confirms the request body schema remains available. See the backend red/green evidence.
- **PC-R05 — contrast:** Added automated contrast checks before changing styles. The red run measured 3.89:1 for guidance text (minimum 4.5:1) and 1.85:1 for the keyboard focus outline (minimum 3:1). Both checks pass after darkening the colors. See the frontend red/green evidence.

Final round 2 checks: `pnpm test` passed 22 tests; `pnpm typecheck` and `pnpm build` passed; the backend portfolio and health tests passed 10 cases; `pip check`, API `compileall`, and `git diff --check` passed. Vite still reports the chart JavaScript bundle above 500 kB. Independent re-review and browser QA on this repaired snapshot are pending.

Round 2 implementation snapshot: `d9f0c83c824cdbcd8d765c19735be400974798b5:sha256:a84d04250e48ad8f658169eab04c74c84fe8206fe7880a85460c0f09cfa3b862` (`evidence/round-2-implementation-snapshot.json`).

## Developer repair evidence — initial round 3

The round 2 independent review found PC-R06 (missing or empty `Content-Type` bypasses exact decimal and duplicate-member decoding) and PC-R07 (deeply nested invalid JSON returns HTTP 500). Tests for both findings were added before changing the decoder. The focused red run had seven behavioral failures: overprecision and duplicate-member bodies returned HTTP 200, nonfinite `NaN` returned HTTP 500 with both omitted and empty `Content-Type`, and a 1,500-level invalid JSON body returned HTTP 500. The non-JSON `text/plain` path already returned HTTP 422 and was covered to guard against fallback decoding. See `evidence/round-3-red.md`.

The route now runs the exact decoder for all nonempty accepted JSON request bodies, including when `Content-Type` is omitted or empty; explicitly rejects other media types with HTTP 422; and converts `RecursionError` from parsing into a serializable HTTP 422. Tests also verify valid requests with missing/empty content type and valid `application/vnd.portfolio+json` requests remain accepted. The focused regression set passed. The full backend API and health suites passed 15 tests; the frontend suite passed 22 tests; frontend typecheck and build, backend `pip check` and `compileall`, and `git diff --check` passed. Vite reports the existing bundle-size warning. See `evidence/round-3-green.md`.

Round 3 implementation snapshot: `d9f0c83c824cdbcd8d765c19735be400974798b5:sha256:64869d6b7fe975d52977b49489835f5ebe79a7225cfd0da2f7c022191d40b51f` (`evidence/round-3-implementation-snapshot.json`). Independent re-review is pending.

## Initial QA available assessment — 2026-11-04 (America/Sao_Paulo)

QA was dispatched independently against s001/p001 and snapshot `d9f0c83c824cdbcd8d765c19735be400974798b5:sha256:64869d6b7fe975d52977b49489835f5ebe79a7225cfd0da2f7c022191d40b51f` after initial review round 3 recorded blocking PC-R08. In Chrome, the QA agent opened a development page on port 5174 and production preview on 4173. It observed both load the form with four allocations at 25.00%, blank dates, and None selected. It opened the chart disclosure in development and observed all six example rows, and observed the form and chart side by side. These partial observations do not establish viewport widths or acceptance of any criterion.

Computer Use then stopped before further interaction with the message: "Computer Use has been stopped for this turn because it could not determine the current browser URL on Windows with enough confidence to enforce policy. Stop your work and send a final message noting why Computer Use ended." The QA agent obeyed that stop and did not use a browser automation fallback. It could not complete interactive browser QA, submission and error scenarios, exact 1280/768 CSS-width checks, or its independent API reproduction; no additional QA tests were run. Browser QA and all acceptance verdicts remain blocked/not assessed. The lead captured the current snapshot after QA returned; its code revision matched the input snapshot. This does not replace a complete before/after QA evidence record or a QA verdict. PC-R08 remains open based on the independent reviewer evidence in review.md.
