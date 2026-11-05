# Frontend

The React and TypeScript single-page app uses Vite, ApexCharts and Axios. It shows an illustrative date-based percentage chart beside a portfolio setup form. The chart's fixed sample values are for display only; they are not historical market data, actual investment performance, or backtest results.

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
- `src/pages/ExampleChart/` contains the page, its example data, chart options, allocation logic, tests and local styles.
- `src/services/portfolio.ts` owns Axios requests and response validation for the portfolio setup API.

If the API is unavailable, the chart still renders and the form displays a retry action when its index list cannot be loaded. A successful form submission only means the server accepted the settings; no portfolio is stored or calculated yet.

See [frontend conventions](AGENTS.md) and [project context](../docs/project-context.md).
