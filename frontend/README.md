# Frontend

The React and TypeScript single-page app uses Vite and ApexCharts. It currently shows one illustrative date-based percentage line chart. Its fixed sample values are for display only; they are not historical market data, actual investment performance, or backtest results.

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

Open `http://127.0.0.1:5173`. Stop the development server with `Ctrl+C`.

## Verify and build

```sh
pnpm test
pnpm typecheck
pnpm build
```

## Source layout

- `src/main.tsx` mounts the single page.
- `src/pages/ExampleChart/` contains the page, its example data, chart options, tests and local styles.
- The remaining `src` directories are reserved for the responsibilities described in their local READMEs. No API or backend is needed to render this example page.

See [frontend conventions](AGENTS.md) and [project context](../docs/project-context.md).
