# Portfolio configuration form and API — plan p001

Proposed 2026-11-04 (America/Sao_Paulo), for approval with specification s001. Spec SHA-256: `1ba23e8edeaf05f02a39fa7e7a95ee9a2ad05ba7be1178d355a29a67a8aabd3f`.

## Architecture and interfaces

1. Keep static index metadata and request validation in the FastAPI API boundary, register focused route(s) in the existing application, and use an explicit request model with decimal-safe validation. The endpoint returns an acknowledgement and calls no domain, getter or storage code. Continue registering the health router. Avoid speculative service and persistence abstractions.
2. Add Axios as a declared frontend dependency and maintain the pnpm lockfile. A small `src/services` module owns HTTP requests and runtime checks of the index and acknowledgement responses, with typed request/response contracts. React state, percentage redistribution and presentation belong with the page/form; keep pure allocation arithmetic isolated where useful for focused coverage, with integer hundredths and deterministic remainder handling.
3. Retain the existing example chart and accessible disclosure. Introduce a page-specific form and responsive layout alongside it. Use native labeled controls, a visible total, clear instructions, keyboard support, and distinct loading and request states. Only selected index allocations are sent.
4. Use same-origin `/api` requests. Configure both Vite development and preview to proxy `/api` to `http://127.0.0.1:8000`, leaving deployment to supply a same-origin reverse proxy. Document both processes and avoid an unrestricted CORS policy. Do not require the API for the chart itself to render.

## Ordered slices

1. Before implementation record Git HEAD, worktree status and the workflow snapshot, preserving existing changes. Record explicit approval of exact s001/p001 hashes.
2. Implement and integrate the backend contract, including invalid input behavior, using meaningful red/green/refactor evidence. Verify health and absence of data-provider/file access.
3. Add the Axios service and allocation logic with focused tests for selection, one/two/four indexes, zeros, decimal boundaries, deterministic remainders and invalid responses. Implement the date and strategy form, pending/feedback states and submission integration; use observable user-facing tests and preserve chart tests.
4. Integrate styles and Vite dev/preview proxy; update frontend and backend usage/contract documentation. Check any durable instruction change only if actually needed.
5. Record implementation snapshot and perform independent review. Address confirmed findings through remaining workflow rounds using regression-first evidence; re-review each changed snapshot. Independent QA then checks every criterion and adverse case, including real browser interactions with both servers and dev/production preview. Follow the workflow correction and final approval gates.

## Verification and integrated run

From the repository root, create `backend/.venv` if needed, install the backend requirements, and run the API:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\backend\.venv\Scripts\python.exe -m uvicorn backend.src.api.main:app --host 127.0.0.1 --port 8000
```

In `frontend`, run `pnpm install --frozen-lockfile`, `pnpm dev --host 127.0.0.1`, and open the reported URL. Run `pnpm test`, `pnpm typecheck`, `pnpm build`, then `pnpm preview --host 127.0.0.1 --port 4173 --strictPort`. Run backend route tests using the backend virtual environment. Resolve existing tool/dependency blockers without claiming a pass.

Browser QA must use the live integrated frontend and API: verify defaults, keyboard and mouse interaction, a single-index allocation, a two-index decimal split, locks and an arbitrary four-index split, selection reset and totals, all six strategies, invalid and equal dates, submit and acknowledgement, retry after API unavailability, and an unsuccessful submission. Inspect requests and responses, verify the chart's label and unchanged contents, direct load/reload, and 1280 px and 768 px layouts with disclosure open. Exercise development and built preview proxy paths; record actual actions and results, not inferred or mock-only outcomes.

Review API validation, decimal precision, async race/error handling, accessibility, dependencies, proxy scope, existing health/chart regressions, documentation and data safety. No final approval is requested until required checks and independent evaluations pass on the current snapshot, with no blocking findings or active assignment. Track TDD, review, QA and snapshot evidence in this task's records.

## Risks and assumptions

Exact 100% across independent controls requires deterministic redistribution; resetting selected shares is visible and explicitly explained. The API's acknowledgement is not a backtest result. Data date availability and financial conventions are unknown and intentionally not inferred. The prior 320 px chart limitation is outside scope by the user's recorded decision. The frontend production host must proxy `/api`; deployment is outside this slice.
