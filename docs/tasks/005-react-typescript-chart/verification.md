# React TypeScript example chart — verification

## Discovery baseline — 2026-11-04 (America/Sao_Paulo)

- HEAD: `b69fee73108494a2cd183f00ee2d5447131b88d8`.
- `git status --porcelain=v1 --untracked-files=all` produced no entries before task-record creation.
- The frontend consists of guidance/README files and has no application package yet.
- `node --version`: `v24.22.1`; `pnpm --version`: `11.25.0`. `npm` was not found on PATH. Dependency registry access and browser availability have not been verified.
- Baseline snapshot: [evidence/baseline-snapshot.json](evidence/baseline-snapshot.json), excluding task and agent-log records per the workflow.
- Discovery handoff snapshot: [evidence/discovery-handoff.json](evidence/discovery-handoff.json); its code revision matches the baseline.

At discovery, no implementation, tests, build, review or browser QA had been performed, and the spec and plan were still proposed. Subsequent evidence is recorded below against its revisions.

## Dependency decision during initial round 1 — 2026-11-04 (America/Sao_Paulo)

- After approval of s001/p001, the first dependency installation installed `apexcharts@8.7.0` and `react-apexcharts@2.2.0`. Both installed package manifests identify their license as `SEE LICENSE IN LICENSE.md`. Their bundled license files describe the vendor's dual-license model. The developer paused work when the [vendor's current license page](https://apexcharts.com/license/) was found to state that installation signifies agreement to applicable terms. Eligibility was not checked. The legal effect of the installation is undetermined. The app now pins the publisher's MIT-licensed `apexcharts@4.7.0` and `react-apexcharts@1.7.0`.
- Read-only registry metadata queries reported `apexcharts@4.7.0` and `react-apexcharts@1.7.0` as MIT. The publisher's [ApexCharts v4.7.0 license](https://github.com/apexcharts/apexcharts.js/blob/v4.7.0/LICENSE) and the [React wrapper license at its 1.7.0 published source revision](https://github.com/apexcharts/react-apexcharts/blob/a62ddf57b5389869dce7e2de0dc4d9a82a025fd0/LICENSE) contain the MIT text. The wrapper's declared peers are `react >=0.13` and `apexcharts >=4.0.0`.
- **Decision:** Continue the same initial round by pinning those exact two MIT-licensed package versions and verifying the approved behavior, build and browser scenarios. These are the same requested libraries; neither approved document fixed a version, so s001/p001 remain unchanged. Pinning prevents an ordinary install from silently selecting the later license model. These older versions may lack subsequent fixes and features; do not assume later upgrades have the same license. Actual installation, compatibility and verification of the proposed pins remain to be established.
- Developer handoff before the version change: the existing test suite reported 2 files/4 tests passing; the latest build failed one chart tooltip TypeScript return-type check. These results applied to the initially installed versions, not the proposed pins. A sandboxed registry probe created an unignored `.pnpm-store` at the repository root; its prior process status could not be confirmed, so the artifact was left intact pending safe handling.

## Initial implementation round 1 evidence — 2026-11-04 (America/Sao_Paulo)

### TDD and compatibility

- **Behavioral red (s001/p001):** `pnpm exec vitest run src/pages/ExampleChart/index.test.tsx` exited 1 against the placeholder page. Vitest discovered and ran the test; it failed at the expected accessible-label assertion because the page did not yet contain the illustrative-data label or chart. This was the observed red before the chart page was implemented.
- An earlier full-suite attempt also failed to resolve the not-yet-created page-local chart module. That was a test setup/import failure, not behavioral red. The focused page test above isolated and recorded the valid red.
- **Green before version decision:** `pnpm test` passed 2 files / 4 tests with the initial chart implementation under ApexCharts 8.7.0 and React wrapper 2.2.0. Those dependencies were later replaced under the recorded license decision; this result is preserved as historical evidence only.
- **Pinned-package compatibility:** after exact MIT pins were installed, `pnpm test` passed 2 files / 4 tests. The page test confirms the line chart receives a datetime axis, six ordered timestamp/value pairs, a negative percentage, and a details table with all six UTC date/value rows. Chart tests cover percentage formatting, the datetime axis and tooltip formatters, and chart dates in `America/Sao_Paulo`, `America/Los_Angeles` and `Asia/Tokyo`.

### Pinned-package commands and observations

- Installed exactly `apexcharts@4.7.0` and `react-apexcharts@1.7.0`; React and React DOM resolved to 19.3.1. `pnpm install --config.confirmModulesPurge=false` completed with exit code 0 and updated the lockfile after the lead's version decision.
- `pnpm install --frozen-lockfile --offline`: exit 0, already up to date.
- `pnpm install --frozen-lockfile`: exit 0, already up to date.
- `pnpm test`: exit 0, 2 files / 4 tests passed.
- `pnpm typecheck`: exit 0.
- `pnpm build`: exit 0. Vite 8.3.5 built the app. The JavaScript chunk was 797.10 kB minified / 225.09 kB gzipped, which produces Vite's advisory for chunks above 500 kB.
- `pnpm dev --host 127.0.0.1`: Vite reported ready in 231 ms at `http://127.0.0.1:5173/`. A local HTTP request to `/` returned status 200 with `text/html`, the root element and the `/src/main.tsx` entry. The development server was stopped after the smoke check.
- Final developer snapshot: [evidence/implementation-round-1.json](evidence/implementation-round-1.json), code revision `186856e0c2f04b0308a585b133ed5e685987b238:sha256:6be2bd67b108ad9a2b2290c50e25be244f9bf9a24398dba9d815f4b8bfe7644c`.
- The generated root `.pnpm-store/` was left intact and added to `.gitignore`; dependency, Vite build and coverage outputs are ignored. Browser interaction, visual responsiveness at 320 px / 1280 px, real chart hover behavior and the independent review remain for the assigned QA/reviewer.

## Initial implementation round 2 evidence — 2026-11-04 (America/Sao_Paulo)

### Regression TDD for CHART-R1-01 and CHART-R1-02

- Added `src/toolingCompatibility.test.ts` to compare the manifest engine range and README prerequisite with the `engines.node` value in the installed, lockfile-selected jsdom manifest. Added `src/pages/ExampleChart/contrast.test.ts` to compute WCAG relative luminance contrast for the configured ApexCharts axis text and the CSS axis caption against the chart card background.
- An initial focused run of the new tests failed before test execution because Vitest's `import.meta.url` was not a file URL in its transformed environment. This was a test setup failure, not behavioral red; the tests were changed to resolve files from Vitest's project working directory before recording behavioral evidence.
- **Observed red before fixes:** `pnpm exec vitest run src/toolingCompatibility.test.ts src/pages/ExampleChart/contrast.test.ts` exited 1 with all four specific assertions failing. The package advertised `>=22.12.0` while locked jsdom 30.1.3 requires `^22.22.2 || ^24.15.0 || >=26.0.0`; the README lacked that required range; axis text contrast was 3.99879185277953:1; and axis caption contrast was 3.1147738977936017:1 against the white card.
- Fixed the manifest and README Node range to `^22.22.2 || ^24.15.0 || >=26.0.0`, matching locked jsdom. Changed ApexCharts axis text and the UTC/unit caption to `#526176`.
- **Observed green:** the same focused Vitest command exited 0 with 2 files / 4 tests passing. `#526176` on the white chart card computes to 6.305839533809002:1, above the test's 4.5:1 minimum for both axis labels and captions.

### Integrated verification

- Environment: `node --version` was `v24.22.1`; `pnpm install --frozen-lockfile` exited 0 (`pnpm` 11.25.0), with no lockfile changes. Reading installed package manifests with Node confirmed `apexcharts@4.7.0`, `react-apexcharts@1.7.0` and `jsdom@30.1.3`; the exact MIT chart pins and prior license decision are unchanged.
- `pnpm list apexcharts react-apexcharts jsdom --depth 0` exited 1 with `[ERR_SQLITE_ERROR] unable to open database file`. The direct manifest read above confirmed installed versions; this package-list command was not needed by the app checks.
- `pnpm test`: exit 0, 4 files / 8 tests passed.
- `pnpm typecheck`: exit 0.
- `pnpm build`: exit 0. Vite 8.3.5 produced a 797.10 kB JavaScript bundle (225.08 kB gzip) and printed its advisory for chunks above 500 kB.
- `git diff --check`: exit 0.
- Updated integrated snapshot: [evidence/implementation-round-2.json](evidence/implementation-round-2.json), code revision `186856e0c2f04b0308a585b133ed5e685987b238:sha256:7f4f5429005c9bd5c1385df8382f3987202b5640ba50f19a49d13e5913de8b86`. The developer snapshot does not replace independent review or browser QA; actual ApexCharts rendering, hover behavior, and the 320 px / 1280 px browser scenarios remain pending.

## Independent QA — 2026-11-04 (America/Sao_Paulo)

- **Revisions:** s001 / p001; code revision `186856e0c2f04b0308a585b133ed5e685987b238:sha256:7f4f5429005c9bd5c1385df8382f3987202b5640ba50f19a49d13e5913de8b86`.
- **Environment and browser actions:** Node 24.22.1, pnpm 11.25.0, Vite 8.3.5. Started the Vite server at `http://127.0.0.1:5173/` and opened that root URL in Chrome. The browser title was `Example percentage chart`; the page reached `document.readyState === "complete"`. Captured a browser screenshot: the viewport was blank white. `document.body.innerText` was empty and `.apexcharts-canvas` count was 0. The browser console reported `Error: Element type is invalid: expected a string (for built-in components) or a class/function (for composite components) but got: object. Check the render method of ExampleChart.` Reloading `/` reproduced the same blank body and React render error.
- **Narrow viewport action:** Set the browser viewport to 320 px wide through the tab's CDP viewport override. Read back `innerWidth=320`, `documentElement.scrollWidth=320`, `body.scrollWidth=320`, `body.innerText=""`, and chart count 0. This confirms the empty failure state has no horizontal overflow; it does not establish that a chart, text, or open disclosure is readable at 320 px. The 1280 px browser scenario, chart hover, disclosure content and actual chart clipping were not checked because the page failed to render.
- Before evaluation: [evidence/qa-dispatch.json](evidence/qa-dispatch.json). After the interrupted browser evaluation: [evidence/qa-after.json](evidence/qa-after.json). The code revisions match. The browser error prevented meaningful exercise of the chart. The CUA turn was interrupted after the 320 px observation; no later UI state or screenshot artifact could be recovered. No application files were changed by QA.

| Criterion | QA result | Expected and actual |
| --- | --- | --- |
| AC-001 | fail | Expected the SPA at `/`; observed the root document shell but an empty body after React failed to render. Reload reproduced the failure. |
| AC-002 | fail | Expected one interactive ApexCharts line and date/percentage hover values; chart count was 0, so no chart or tooltip appeared. |
| AC-003 | fail | Expected the visible illustrative label and six exact values; the body was empty, so none were presented. |
| AC-004 | fail | Expected a heading, description, all-pair text alternative and readable chart at 320 px and 1280 px. No content appeared. At 320 px only the empty body fit; 1280 px, the disclosure and clipping could not be verified. |
| AC-005 | blocked | Expected the visible page to render from local example data without backend or external data. The failing render prevented independent runtime verification; this criterion remains unassessed. |
| AC-006 | not_run | Expected successful clean installation, development, build and documented prerequisites/layout. QA did not independently run the commands or verify source placement; the blank browser result does not establish this criterion. |

**Verdict: failed due to an implementation defect.** This QA found the root page's blank-render failure, independent of the round-2 source/test review. No cause beyond the observed React render exception is assigned. Expected hover, positive/negative tooltip comparisons, 1280 px layout, open-details behavior and UTC browser checks remain not run because the chart was absent. Do not treat the empty 320 px body's lack of overflow as a responsive pass.

## Correction implementation round 1 — 2026-11-04 (America/Sao_Paulo)

Scope: s001/p002, CHART-QA-01 and AC-001–AC-006. Input snapshot `4371d83c90b5306b05eef12ee7395e2912dce711:sha256:10deab40d50411e871720265cd8748b495f3bd5eb9b869591de04d51da9cf1ad`; output [snapshot](evidence/correction-implementation-1.json).

Before production changes, Chrome loaded `http://127.0.0.1:5174/` from `pnpm dev --host 127.0.0.1 --port 5174 --strictPort`: blank page, zero `.apexcharts-canvas` elements (expected one), and React reported `Element type is invalid ... got: object` in `ExampleChart`. Port 5173 was already in use, so an independently started strict port 5174 was used. Screenshot was observed but not retained. The focused `pnpm test src/pages/ExampleChart/interop.test.tsx` failed before the fix with the same invalid element type error. After the adapter, this regression and the existing callable-default page test both passed: `pnpm test src/pages/ExampleChart/interop.test.tsx src/pages/ExampleChart/index.test.tsx` (2 tests). The adapter checks both shapes and raises an explicit diagnostic for unsupported shapes.

An additional actual browser regression was observed on freshly loaded production preview at 320 px: adjacent visible x-axis label bounding boxes overlapped (first right 92.964 vs next left 92.883; second right 136.433 vs next left 135.578). After the responsive UTC month formatting change, fresh dev and preview at 320 px produced separated labels (first right 79.531, next left 106.250), six markers, chart bounds 17–303 px and document scroll width 320 px. The existing UTC test was extended to cover the narrow formatter in three controlled time zones. At 1280 px preview, labels were separated and document scroll width was 1280 px. Resizing dev from 1280 to 320 produced canvas and SVG bounds 17–303 px and document scroll width 320 px. Narrow and wide visual screenshots were inspected but not retained.

Chrome checked real pinned chart on dev 5174 and fresh production preview `pnpm preview --host 127.0.0.1 --port 4173 --strictPort`: one canvas after direct load and reload, visible percentage axes, and point hover text `2024-02-01 Example percentage: 2.5%` and `2024-03-01 Example percentage: -1.2%` on both. Preview disclosure showed all six date/value rows. Verification used local browser DOM inspection and CDP mouse movement; the preview and dev servers require no backend. Browser viewport override was reset. The planned strict port 5173 dev command was blocked by an existing unrelated listener; the same command on 5174 was used for this implementation check.

`pnpm install --frozen-lockfile` passed with pnpm 11.25.0 and Node v24.22.1 after the sandboxed store access failed; the successful install used the existing pnpm store with elevated permissions. Final `pnpm test` passed 5 files/9 tests, `pnpm typecheck` passed, and `pnpm build` passed with Vite's >500 kB chunk warning (797.49 kB). `git diff --check` passed, with a Git line-ending warning on the task state file. No refactor beyond the small local adapter and responsive formatter was needed; final full tests and build provide the green/refactor evidence. Independent review and QA remain pending.

## Independent correction QA — 2026-11-04 (America/Sao_Paulo)

- **Revisions:** s001 SHA-256 18579d0e36c51729f0c4d7ff86601837ee9d08ec8923e35ef558fec70656da57; p002 SHA-256 92b281a4b439477445670a51a5c9bae5be7ac0cc6093adec88e909cec1a884bb; code snapshot 4371d83c90b5306b05eef12ee7395e2912dce711:sha256:c59496554d0de6a25f22d5d41967f51f6e685517588dedf68ecbb489f1824edc. The [before](evidence/qa-correction-1-before.json) and [after](evidence/qa-correction-1-after.json) snapshots match.
- **Environment and actions:** Chrome via the browser control tool; Node v24.22.1, pnpm 11.25.0, Vite 8.3.5. Started the documented frontend development server on http://127.0.0.1:5173/ with pnpm dev --host 127.0.0.1 --port 5173 --strictPort, and the production build preview on http://127.0.0.1:4173/ with pnpm preview --host 127.0.0.1 --port 4173 --strictPort. Direct root loads and reloads of both pages rendered one .apexcharts-canvas and six markers. Browser viewport overrides were reset and the QA tabs and servers were closed.
- **AC-001 — pass:** Both dev and production preview render the SPA on a direct root load and after reload.
- **AC-002 — pass:** The real chart displayed date and percentage axes on dev and preview. Hovering the February and March markers showed 2024-02-01 / 2.5% and 2024-03-01 / -1.2%, matching the source rows.
- **AC-003 — pass:** The visible illustrative-data label appeared on both pages. Opening the native disclosure exposed all six chronological UTC date/value rows: 2024-01-01 / 0.0%, 2024-02-01 / 2.5%, 2024-03-01 / -1.2%, 2024-04-01 / 3.8%, 2024-05-01 / 2.0%, 2024-06-01 / 5.1%. Hover dates remained on those UTC dates. pnpm test also passed the chart formatter checks under America/Sao_Paulo, America/Los_Angeles and Asia/Tokyo.
- **AC-004 — fail, finding CHART-QA-02:** At 1280 px, the chart labels, description and open disclosure were readable, and document client width and scroll width both measured 1280 px. At 320 px with the disclosure closed, the chart bounds were x=17 to 303 px and document client/scroll widths both measured 320 px. Month labels were separated. Opening the six-row disclosure created vertical page scrolling. In both dev and preview, innerWidth was 320 px, but document.scrollingElement.clientWidth was 305 px while its scrollWidth was 320 px; the body computed min-width: 320px. The screenshot showed the page-level horizontal scrollbar. The chart itself remained within x=17 to 303 px and was not clipped, but the required no-page-overflow condition fails in this supported disclosure state. The defect reproduces in both browser paths and is within AC-004.
- **AC-005 — pass:** The page rendered its fixed series without a backend or market-data file. The dev page used only same-origin Vite entry scripts; the preview loaded only same-origin built JS and CSS assets. The rendered page had no iframe or form.
- **AC-006 — pass:** From frontend, pnpm install --frozen-lockfile passed; pnpm test passed 5 files / 9 tests; pnpm typecheck passed; and pnpm build passed. The build reports Vite's advisory for the 797.49 kB minified JS chunk. README prerequisites, frozen install, development, preview and source-layout instructions were present and used. The first git diff --check found an extra blank line at the end of this task record; that record whitespace has been trimmed and the final diff check passed.
- **Independent final checks:** git diff --check passed after the task-record newline cleanup. No application files were changed during QA. The code snapshot remained unchanged before and after evaluation. The production build's dist output is ignored.

**Verdict: failed due to an implementation defect.** CHART-QA-01 is resolved by independent direct-load and reload observations in both dev and production preview. CHART-QA-02 blocks AC-004 because opening the accessible data disclosure at a 320 px viewport exposes 15 px of page-level horizontal overflow. Correction QA found this defect after the single allowed correction cycle; route it through the feature-workflow human-intervention gate. Preserve the original failed QA verdict and its evidence.

## Correction lead audit — 2026-11-04 (America/Sao_Paulo)

The current code snapshot matches the developer handoff and both the before and after independent review and QA snapshots. Review passed. Independent Chrome QA resolved CHART-QA-01 on the planned dev and production preview ports. AC-001, AC-002, AC-003, AC-005 and AC-006 passed. Frozen install, nine tests, type checking, the production build and the final diff check passed. The frontend README covers the verified prerequisites and commands.

CHART-QA-02 blocks AC-004 on both browser paths when the disclosure is open at 320 px. The independent QA width comparison used the document client width, which excludes the vertical scrollbar. The prior implementation check compared scroll width with the window width. Per p002 step 5 and feature-workflow section 4, the task moves to `needs_human_intervention` with the original verdicts and counters preserved. Final approval is pending resolution of the failed criterion.

Proposed repair for human authorization: reproduce the 320 px open-disclosure overflow with a browser regression that compares the document client and scroll widths. Remove the fixed 320 px body minimum if the regression confirms the cause. Repeat the narrow and wide browser checks, independent review and QA on the resulting snapshot.

## Human scope decision - 2026-11-04 (America/Sao_Paulo)

The user accepted CHART-QA-02 as outside intended use: "So its good enough. The dashboard is not meant to be used in such small screen"

The measured 320 px overflow and failed s001/p002 AC-004 verdict remain recorded. The [scope amendment snapshot](evidence/scope-amendment-resume.json) matches all files covered by the p002 QA snapshot. The intervening Git commit changed only the agent log. Proposed s002 removes the 320 px acceptance check and retains the 1280 px layout and accessible six-row disclosure requirements. Proposed p003 describes independent verification of the amended scope without implementation changes. Both revisions await explicit reapproval before independent evaluation and final approval.
