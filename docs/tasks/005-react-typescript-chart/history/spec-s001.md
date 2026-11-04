# React TypeScript example chart — specification s001

Status: proposed; awaiting explicit human approval with plan p001. Date: 2026-11-04 (America/Sao_Paulo).

## Goal and scope

Start a single-page React and TypeScript application in `frontend` that displays one ApexCharts line chart. Its x-axis represents dates and its y-axis represents percentages. Populate it entirely from a small fixed example series in the frontend for now.

## Assumptions and proposed choices

- The page is a simple chart demonstration, without portfolio or market-performance claims. Clearly label the numbers as illustrative example data. They are not historical market data or calculated returns.
- Use the following arbitrary points to exercise both positive and negative percentages. Each numeric value is already a percentage: `2.5` displays as `2.5%`; it is not multiplied by 100.

  | Date (UTC) | Example percentage |
  | --- | ---: |
  | 2024-01-01 | 0.0% |
  | 2024-02-01 | 2.5% |
  | 2024-03-01 | -1.2% |
  | 2024-04-01 | 3.8% |
  | 2024-05-01 | 2.0% |
  | 2024-06-01 | 5.1% |

- Interpret the dates consistently as UTC calendar dates so local time zones do not shift them to another day. Use a date-based x-axis, not an arbitrary category axis. Provide a percentage label on the y-axis and percentage values in tooltips.
- Provide a short accessible description and an accessible text alternative containing the example dates and values; keep the chart usable at desktop and narrow mobile widths.
- One page at the application root is sufficient. A router, portfolio calculations, data loading, filters and authentication are outside this slice. No real datasets, sources, backend endpoints, financial conventions or source files are changed.

## Acceptance criteria

- **AC-001 — Application:** From a clean checkout, the documented frontend installation and development commands start a React + TypeScript single-page application at the root URL. The documented production build completes successfully.
- **AC-002 — Chart:** The page displays one ApexCharts line chart with a date-based x-axis and a y-axis whose labels show percentages. Hovering a plotted point presents its date and percentage value consistently with its data point.
- **AC-003 — Example data:** The fixed six points above appear in chronological order; their numeric values are treated as percentages as shown, including the negative example. The page visibly identifies the data as illustrative. Dates presented in the chart/tooltip and text alternative use the same UTC calendar dates.
- **AC-004 — Accessible and responsive presentation:** The page has a meaningful heading, a description of the chart, and an accessible text alternative for all six date/value pairs. At 320 px and 1280 px viewport widths, the chart and its description remain readable without page-level horizontal overflow or clipped chart content.
- **AC-005 — Boundaries:** The example data stays in the frontend, and the page does not require a backend, external data service, or market-data file to render. No historical results, financial calculations, or portfolio behavior are implied or implemented.
- **AC-006 — Organization and usage:** Application code follows the existing `frontend/AGENTS.md` and each `frontend/src` folder README: page-specific chart, data and local styling live with the page; reusable components are placed in `src/components` only if genuinely reused. Necessary frontend bootstrap/configuration files live at the frontend root or `src` entry point. The frontend README documents prerequisites, install, run, build and verification commands.

## Adverse cases and exclusions

- Verify a negative value retains its minus sign and percent suffix, and date display remains consistent across at least two browser time zones or equivalent controlled formatting checks.
- Verify narrow and wide layouts, a direct load/reload of the root page, and that the accessible alternative contains all pairs even if a user cannot interpret the visual chart.
- Empty, malformed, loading and remote-error data states are not introduced because this slice uses only fixed local data. Live prices, backtest results, comparison series, interactive filters and deployment are outside scope.

## Human decisions

The user requested React with TypeScript, an SPA, ApexCharts, dates on x, percentages on y, and permits frontend mock data. The fixed points, UTC display, minimal single-page layout and accessible text alternative above are proposed implementation choices pending approval. No financial interpretation is established.
