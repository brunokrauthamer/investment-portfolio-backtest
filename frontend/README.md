# Frontend

The React and TypeScript single-page app uses Vite, ApexCharts and Axios. It shows the cumulative return chart beside a portfolio setup form. The chart appears after a successful request to `POST /api/portfolio`; before that, the page shows an empty state rather than sample performance values.

The chart dependencies are pinned to `apexcharts` 4.7.0 and `react-apexcharts` 1.7.0. ApexCharts changed to a dual-license model in later releases, so review the applicable license before changing either pin; a semver range could otherwise select a version with different terms.

## Requirements

- Node.js versions: `^22.22.2 || ^24.15.0 || >=26.0.0` (the range required by locked jsdom 30.1.3).
- pnpm 11.25 or newer.

## Install and run

From this directory:

```sh
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

In another terminal, start the API from the repository root using the backend setup in [the backend README](../backend/README.md). The Vite development and preview servers proxy `/api` requests to `http://127.0.0.1:8000`; a production host must provide the same-origin proxy. Open `http://127.0.0.1:5173`. Stop either server with `Ctrl+C`.

## Verify and build

```sh
pnpm test
pnpm typecheck
pnpm build
pnpm preview --host 127.0.0.1 --port 4173 --strictPort
```

The preview command serves the production build at `http://127.0.0.1:4173`.

## Source layout

- `src/main.tsx` mounts the single page.
- `src/pages/ExampleChart/` contains the page, chart options, allocation logic, tests and local styles.
- `src/services/portfolio.ts` owns Axios requests and response validation for the portfolio API.

The form uses default dates of 2011-01-04 and 2026-10-30. A successful response's `series` is passed directly to ApexCharts without reshaping. The chart tooltip includes each point's date, daily return and cumulative return. Empty ranges and request failures have separate messages, and changing the form clears the previous result. The development and preview servers use the same-origin API proxy described above.

See [frontend conventions](AGENTS.md) and [project context](../docs/project-context.md).
