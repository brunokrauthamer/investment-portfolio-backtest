# React TypeScript example chart — review

At discovery, specification s001 and plan p001 awaited human approval.

## Initial round 1 — 2026-11-04 (America/Sao_Paulo)

**Verdict: changes required.** Approved s001 (`18579d0e36c51729f0c4d7ff86601837ee9d08ec8923e35ef558fec70656da57`) and p001 (`6e86712794b7b6ac6b86392cd635da4a540b827e3f462626f65c7e2b252fec43`) were confirmed by SHA-256. Code revision `186856e0c2f04b0308a585b133ed5e685987b238:sha256:6be2bd67b108ad9a2b2290c50e25be244f9bf9a24398dba9d815f4b8bfe7644c` matches both [before](evidence/review-initial-1-before.json) and [after](evidence/review-initial-1-after.json) snapshots.

- **CHART-R1-01, P2, blocking, AC-001 and AC-006.** `frontend/README.md:9` and `frontend/package.json:8` advertise Node.js 22.12 or newer. The direct locked dependency `jsdom@30.1.3` (`frontend/pnpm-lock.yaml:446-448` and its installed manifest) declares `^22.22.2 || ^24.15.0 || >=26.0.0`. Several locked dependencies declare the same range, including `@asamuzakjp/css-color` and `@asamuzakjp/dom-selector`. Comparing these files reproduces the mismatch: Node 22.12 and 24.0 are advertised and outside the supported test environment. A clean setup following the README can select an unsupported runtime for verification. The current commands passed on 24.22.1. No lower runtime was executed. Align the documented and manifest ranges with the selected toolchain, or select a toolchain that supports the advertised range.
- **CHART-R1-02, P2, blocking, AC-004.** The 11 px chart labels use `#748093` (`frontend/src/pages/ExampleChart/chart.ts:47,85,93`), inherited through ApexCharts' SVG text fill. The 11 px axis caption uses `#8893a2` (`frontend/src/pages/ExampleChart/index.css:100-105`). Against the white card (`index.css:14`), these yield 4.00:1 and 3.11:1 respectively, computed from the assigned foreground/background hex values using relative luminance. They fall below the ordinary-text legibility benchmark of 4.5:1, making dates, percentages, and the UTC/unit captions harder to read for people with reduced contrast sensitivity. Increase contrast for the chart labels and captions. [W3C contrast benchmark and calculation](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)

### Independent checks and scope

- On Node 24.22.1 and pnpm 11.25.0, ran `pnpm install --frozen-lockfile --offline`, `pnpm test` (4 tests across 2 files), and `pnpm build`, all exit 0. `git diff --check` exited 0. The build reported an advisory for the 797.10 kB minified JS bundle (225.09 kB gzip). No bundle limit is part of s001.
- Inspected tracked diff, all untracked frontend files and the lockfile, along with existing folder guidance. The bootstrap and page code follow the proposed architecture. The lockfile and local manifests contain the exact recorded MIT versions, and generated dependency/build/store artifacts are ignored.
- Source inspection verified one local six-point UTC series feeding the chart and table, the percentage and tooltip formatters, and the native details disclosure. Tests cover the page and formatting contract through the chart wrapper mock and controlled time zones. Real chart rendering, hover, and the 320 px and 1280 px layouts still require independent browser QA after the review gate.

## Initial round 2 — 2026-11-04 (America/Sao_Paulo)

**Verdict: passed.** Confirmed SHA-256 for s001 (`18579d0e36c51729f0c4d7ff86601837ee9d08ec8923e35ef558fec70656da57`) and p001 (`6e86712794b7b6ac6b86392cd635da4a540b827e3f462626f65c7e2b252fec43`). Code revision `186856e0c2f04b0308a585b133ed5e685987b238:sha256:7f4f5429005c9bd5c1385df8382f3987202b5640ba50f19a49d13e5913de8b86` matches the assignment. The [before](evidence/review-initial-2-before.json) and [after](evidence/review-initial-2-after.json) snapshot files have identical SHA-256 hashes.

- **CHART-R1-01 resolved (AC-001, AC-006).** The frontend manifest and README both declare `^22.22.2 || ^24.15.0 || >=26.0.0`, matching installed and locked jsdom 30.1.3. The other Node engine declarations in the lockfile allow this range. The compatibility regressions read the installed jsdom manifest and check the documented and declared ranges. Executable checks used Node 24.22.1 and pnpm 11.25.0.
- **CHART-R1-02 resolved (AC-004).** ApexCharts' SVG labels inherit `chart.foreColor` when their label styles do not supply a color. Independently calculating luminance for `#526176` against the white card gives 6.306:1 for both axis labels and captions. The chart description's `#69778a` yields 4.559:1 on the same background. The added regressions assert a minimum of 4.5:1 for both parts of the reported defect.

### Independent checks and scope

- Ran `pnpm install --frozen-lockfile --offline`, `pnpm test` (8 tests across 4 files), `pnpm build` (includes TypeScript checking), and `git diff --check`. All exited 0. Vite reports an advisory for the 797.10 kB minified JavaScript chunk (225.08 kB gzip). The approved spec has no bundle size threshold.
- Reviewed the tracked diff, all untracked frontend files including tests and the lockfile, and the repository and frontend folder guidance. The Vite entry mounts one page. One page-local series supplies the chart and the keyboard-operable native disclosure table. The installed chart source defaults datetime ticks to UTC and passes the point index to the tooltip formatter. Both ApexCharts dependency pins remain exact. The frontend uses local sample data and needs no service or market data input.
- No new actionable findings within s001 and p001. Independent browser QA remains pending for actual rendering, tooltip hover, reload, disclosure, and chart readability at 320 px and 1280 px. Include a horizontal overflow check at 320 px with the table open because the body declares a 320 px minimum width.
