# React TypeScript example chart — plan p001

Status: proposed; awaiting explicit human approval with specification s001. Date: 2026-11-04 (America/Sao_Paulo).

## Architecture and boundaries

Use Vite to bootstrap React + TypeScript in `frontend`, with `apexcharts` and its React wrapper `react-apexcharts`. Vite supplies the single entry page and local development/build tooling; no router is needed for one root page. Use `pnpm` and commit its lockfile so dependencies are reproducible; `pnpm` 11.25.0 and Node 24.22.1 were found during discovery. The implemented README must state the actual supported Node and pnpm prerequisites for the selected dependencies.

Place the application entry point in `frontend/src/main.tsx`, and the one page with its local data, chart options and CSS under `frontend/src/pages/ExampleChart/` with an `index.tsx` page entry. Configure ApexCharts as a line chart: UTC timestamps for the x-values, `datetime` x-axis with UTC date formatting, percentage-formatted y-axis and tooltip. Present a heading and an example-data label, plus an accessible text alternative for all six pairs. Keep page-specific logic with the page; introduce a reusable component under `src/components` only if an actual shared responsibility emerges. Existing services, store, assets and shared folders remain available for their documented future roles.

Data flows from one page-local immutable example series into both the chart and the accessible alternative. No service, network data request, domain calculation or new cross-layer abstraction is needed. This keeps display values synchronized without implying financial meaning. Use semantic HTML and accessible names where appropriate; avoid adding controls that do not serve the requested chart.

## Ordered implementation slices

1. Record the approved s001/p001 hashes, baseline and implementation assignment. Establish the frontend package manifest, lockfile, Vite/TypeScript entry and a meaningful first failing behavioral test for the page and example-series contract.
2. Implement the example chart and its text alternative, styling and responsive behavior; make the focused tests pass. Add targeted tests for percentage/date formatting and the negative value, with a chart-wrapper mock only where necessary to test the page contract. Record observed red/green/refactor evidence. Verify real chart rendering separately in a browser.
3. Update `frontend/README.md` with the actual prerequisites, install, development, build and verification commands. Ensure generated dependency/build directories are ignored without excluding the lockfile. Run the applicable focused checks and build, take the integrated snapshot and return the writer token.
4. Have an independent reviewer evaluate the complete integrated snapshot against s001/p001, tests, architecture and documentation. Resolve actionable findings within the workflow's bounded rounds, using failing regression tests before fixes, then re-review.
5. Have independent QA check every criterion and adverse case on the matching snapshot, including browser execution. At root URL, observe the actual chart, hover a positive and a negative point, compare displayed dates/percentages to the text alternative, reload, and inspect 320 px and 1280 px widths. Check the UTC date behavior in two controlled time zones or equivalent. Record actual actions, expected/actual results and limitations.
6. Audit documentation, findings, snapshots and all criteria; rerun affected checks on the final snapshot and request final human approval after all required evaluations pass.

## Verification and run instructions

Expected commands from `frontend`: `pnpm install --frozen-lockfile`, `pnpm dev --host 127.0.0.1`, `pnpm build`, and the test command defined in the manifest (expected `pnpm test --run`). Final commands and versions must be recorded as actually run. Use meaningful tests for the user-visible data/format contract and retain independent browser QA; source inspection, mocks and a successful build alone cannot establish that ApexCharts actually renders.

Capture workflow snapshots before and after independent evaluation; changes to application code, configuration, tests or durable documentation require the applicable re-review and QA on the new snapshot. Keep generated files out of source control. The first implementation has not started.

## Risks and decisions

- The frontend has no existing package setup. `pnpm` is available locally, but dependency registry/network access has not been verified; treat unavailable dependencies as an environment blocker rather than inventing a successful build.
- Chart libraries handle dates and layout internally. Explicit UTC behavior, browser checks and a text alternative mitigate shifted dates, clipped labels and inaccessible visual-only information.
- The sample is intentionally fabricated for display only; visible labeling prevents it being mistaken for historical market or backtest data.
- Vite plus the official React wrapper is a small conventional setup for the requested libraries. A router, data service and generic chart abstraction add no demonstrated value for this single-page slice.
