# Specification s001: Multiple portfolio results

Workflow: simple-feature-workflow.

## Goal and scope

Keep the existing one-portfolio-per-submission frontend flow and append each valid API result to a shared chart and characteristics list. The user clarified that the future POST `/api/portfolio` response will match their stated contract and approved frontend-only implementation despite the current acknowledgement-only backend. Do not change backend behavior or introduce financial calculations or production mock results.

## Acceptance criteria

- A1: Each valid successful response contains exactly one named series and an array of points with UTC Unix-millisecond `x`, cumulative-return-percent `y`, UTC `date`, `daily_return_pct`, and `cumulative_return_pct`. Validate responses, accepting an empty data array and explicitly showing that no data was returned. Invalid responses and failed requests show errors and preserve the form and prior results.
- A2: Every valid success appends a UI-only entry containing its returned series, independent snapshot of the submitted allocations, dates, and rebalancing strategy, stable color, identifier, and monotonically assigned `Portfolio N` label. Reset the form to its existing initial state only after valid success. Do not send the identifier to the API.
- A3: Render all retained entries on the ApexCharts chart with their frontend labels and direct API `x` and `y` values. Use UTC dates for labels or tooltips. Treat percentage values as already expressed in percent; perform no return calculations or rescaling.
- A4: Show a characteristics card for each snapshot with its chart color and accessible remove action. Removal deletes the matching card and chart series without a request and preserves other entries' labels and colors. Support arbitrarily many results without a hardcoded count limit.
- A5: Distinguish loading, failure, invalid responses, valid empty results, and the initial no-results state. Preserve existing index loading, validation, form controls and styling conventions. Eliminate production example values, series, notices and table.

## Decisions and constraints

The original user request specifies the complete response shape and direct treatment of returns. The user subsequently authorized assuming that future response shape and requested no backend changes. The current backend returns only `{"status":"ok"}`, which the frontend will reject until the backend contract changes. Approval: user message `Approve and proceed`, 2026-11-04, America/Sao_Paulo.
