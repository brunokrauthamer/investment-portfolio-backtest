# Independent review

## Initial round 1 — 2026-11-04 (America/Sao_Paulo)

**Verdict: changes required.** Four blocking findings on AC-002 and AC-004 and one nonblocking accessibility finding on AC-002. Spec `s001` SHA-256 `1ba23e8edeaf05f02a39fa7e7a95ee9a2ad05ba7be1178d355a29a67a8aabd3f`; plan `p001` SHA-256 `106e4271058d71e3ce78f5c8466b0eda50a1c0ec60d867b6eec0d469191bda8e`. The [before](evidence/review-initial-round-1-before.json) and [after](evidence/review-initial-round-1-after.json) snapshots match `d9f0c83c824cdbcd8d765c19735be400974798b5:sha256:e98ee29168c73ac180e43e12e4a6a800c55de4ae9b91584a8490f0e27b03fe46`.

### Findings

- **PC-R01, P1, blocking — AC-002 and AC-004. Previously edited percentage fields show stale shares.** `frontend/src/pages/ExampleChart/index.tsx:129` retains a draft for each edited input. Redistribution updates allocation state without clearing inactive drafts, and line 368 prefers each stale draft over the committed share. In Chrome, enter 40 for IBOVESPA, Tab, then 50 for IFIX and Tab. The displayed fields read `40.00, 50.00, 12.50, 12.50` (115%) while the total reads `100.00%` and the real request submits `25, 50, 12.5, 12.5`. Keep unfinished input text local to an active edit, and ensure every settled field displays its committed allocation after redistribution. [Reproduction](evidence/review-initial-round-1-browser.py) and [output](evidence/review-initial-round-1-browser.txt).
- **PC-R02, P2, blocking — AC-002 and AC-004. Enter can submit a rejected edit.** `frontend/src/pages/ExampleChart/index.tsx:156` validates committed totals only, while the text input at line 367 has a shape pattern that accepts `101` and its `min`/`max` do not constrain text. With valid dates, type `101` into IFIX and leave focus in that field. The field reports an invalid percentage. Press Enter and the browser sends the previous allocation, receives HTTP 200 and shows success while the invalid draft is visible. Block submission until the draft is valid or visibly restored. [Browser output](evidence/review-initial-round-1-browser.txt).
- **PC-R03, P2, blocking — AC-004. JSON number parsing loses precision before validation and can return 500.** `backend/src/api/controller/portfolio.py:33` converts a number already decoded as a binary float into `Decimal`, too late to recover the original JSON value. On a valid body with one IFIX allocation, raw JSON percentage tokens `99.9999999999999999` and `100.0000000000000001` are each incorrectly acknowledged as 100. A raw `1e309` or `NaN` receives 500 because the nonfinite input cannot be serialized in the validation response. Preserve exact decimal input before validating range, scale and total, and return a serializable 422 for invalid numeric tokens. [Raw HTTP cases](evidence/review-initial-round-1-api.txt).
- **PC-R04, P2, blocking — AC-004. Repeated JSON fields are accepted.** The default JSON parsing before `backend/src/api/controller/portfolio.py:80` discards duplicate keys before `extra="forbid"` and the model validators can see them. A valid outer body with `{"index":"ifix","percentage":50,"percentage":100}` in `allocations` returns HTTP 200 using the last key. Spec s001 requires HTTP 422 for duplicated fields. Reject repeated JSON member names during decoding for the portfolio request. [Raw HTTP cases](evidence/review-initial-round-1-api.txt).
- **PC-R05, P3, nonblocking — AC-002. Allocation instructions and keyboard focus have low contrast.** `frontend/src/pages/ExampleChart/index.css:100` renders essential allocation behavior in 11 px `#758297` on white (3.89:1). The new input, select and button focus styling at line 191 uses `#8ecabd`, with 1.85:1 contrast against white. Darken both so users can read the redistribution guidance and track keyboard focus reliably. Ratios calculated from the declared sRGB colors and the white card background.

### Checks and scope

- Inspected the full tracked application diff, the four untracked implementation and test files, the dependency lockfile changes, documentation, chart and health boundaries, and the approved revision hashes. No getter, domain calculation or market data edits or calls appear in the changes.
- Ran the existing frontend suite (`pnpm test`, 18 passed) and the backend health and portfolio contract suites in `backend/.venv` (7 passed). The existing tests do not exercise the findings above. [Frontend results](evidence/review-initial-round-1-frontend-tests.txt) and [backend results](evidence/review-initial-round-1-backend-tests.txt).
- The separate Chrome probe used live Vite development and FastAPI servers and observed four 25.00% defaults, a successful request, and no page-level horizontal overflow with the disclosure open at 1280 px and 768 px. Panels were side by side at 1280 px and stacked at 768 px. This review probe leaves independent integrated QA pending.
- `git diff --check` passed with line-ending notices. The matching before and after snapshots establish that review evaluated the developer handoff without changing implementation files.

Return the blocking findings for a regression-first fix within the remaining initial rounds and re-review the resulting snapshot.

## Initial round 2 — 2026-11-04 (America/Sao_Paulo)

**Verdict: changes required.** Two blocking AC-004 findings remain. Spec `s001` SHA-256 `1ba23e8edeaf05f02a39fa7e7a95ee9a2ad05ba7be1178d355a29a67a8aabd3f` and plan `p001` SHA-256 `106e4271058d71e3ce78f5c8466b0eda50a1c0ec60d867b6eec0d469191bda8e` match approval. The [before](evidence/review-initial-round-2-before.json) and [after](evidence/review-initial-round-2-after.json) snapshots match `d9f0c83c824cdbcd8d765c19735be400974798b5:sha256:a84d04250e48ad8f658169eab04c74c84fe8206fe7880a85460c0f09cfa3b862`.

### Recheck of round 1 findings

- **PC-R01 and PC-R02 resolved.** In Chrome against the live Vite and FastAPI servers, editing IBOVESPA to 40 and then IFIX to 50 settled the four fields at 25.00, 50.00, 12.50 and 12.50. The total was 100.00%, the successful request sent the same shares, and entering 101 in a focused field displayed an error. Pressing Enter sent zero requests, and Tab restored the committed share. [Probe](evidence/review-initial-round-2-browser.py) and [output](evidence/review-initial-round-2-browser.txt).
- **PC-R03 and PC-R04 original reproductions fixed for explicit JSON media types.** With either `application/json` or `application/vnd.portfolio+json`, the exact overprecision, nonfinite and repeated key cases now return 422. A valid 100% submission returns 200. The same inputs can still bypass validation through PC-R06, so these findings remain open pending that repair. [API output](evidence/review-initial-round-2-api.txt).
- **PC-R05 resolved.** Chrome computed 6.29:1 for guidance and 6.31:1 for the actual keyboard focus outline against the white form card. [Browser output](evidence/review-initial-round-2-browser.txt).

### Findings

- **PC-R06, P2, blocking — AC-004. Missing or empty Content-Type bypasses exact JSON parsing.** The wrapper at `backend/src/api/controller/portfolio.py:60` runs only for an explicit JSON media type. FastAPI 0.128.8 parses the same body as JSON when the header is omitted or empty, using its ordinary parser. For a JSON body with valid dates, one IFIX allocation and rebalancing set to `none`, omit the header and send `99.9999999999999999` as its percentage, or include two `percentage` members with values 50 and 100. Both requests receive 200. `1e309` and `NaN` receive 500. The API needs one validation path for all JSON accepted by the route, or an explicit rejection of missing media type before FastAPI falls back. [Reproduction output](evidence/review-initial-round-2-api.txt).
- **PC-R07, P3, blocking — AC-004. A deeply nested invalid body escapes as HTTP 500.** The new decoder at `backend/src/api/controller/portfolio.py:67` does not catch the recursion error raised by `json.loads`. With `Content-Type: application/json`, send `{"unexpected":` followed by 1,500 opening brackets, `0`, 1,500 closing brackets and `}`. The route returns 500 instead of the contract's 422 for an invalid body. Reject parser depth errors with a serializable validation response. [Reproduction output](evidence/review-initial-round-2-api.txt).

### Checks and scope

- Independently ran all 22 frontend tests and 10 backend API and health tests. All passed. `git diff --check` passed with line ending notices. [Frontend results](evidence/review-initial-round-2-frontend-tests.txt) and [backend results](evidence/review-initial-round-2-backend-tests.txt).
- Inspected the full integrated app diff, including new untracked service, allocation helper, controller and contract tests. The source review covered the exact index list and Axios loading, allocation arithmetic and locking, date and strategy controls, request validation and feedback, responsive CSS and both Vite proxy configurations. The dependency and run documentation agree with the implementation. The snapshot introduces no acquisition, data or domain changes. Independent acceptance QA remains pending.

Route PC-R06 and PC-R07 to the remaining initial implementation round, then independently recheck the resulting snapshot.

## Initial round 3 — 2026-11-04 (America/Sao_Paulo)

**Verdict: changes required.** One blocking AC-004 finding remains. The approved spec `s001` SHA-256 `1ba23e8edeaf05f02a39fa7e7a95ee9a2ad05ba7be1178d355a29a67a8aabd3f` and plan `p001` SHA-256 `106e4271058d71e3ce78f5c8466b0eda50a1c0ec60d867b6eec0d469191bda8e` match the files reviewed. The [before](evidence/review-initial-round-3-before.json) and [after](evidence/review-initial-round-3-after.json) snapshots both identify `d9f0c83c824cdbcd8d765c19735be400974798b5:sha256:64869d6b7fe975d52977b49489835f5ebe79a7225cfd0da2f7c022191d40b51f`.

### Recheck of earlier findings

- **PC-R03, PC-R04 and PC-R06 resolved.** A valid request returned HTTP 200 and the exact acknowledgement with an omitted or empty Content-Type, plain `application/json`, uppercase `APPLICATION/JSON` with a charset parameter and `application/vnd.portfolio+json`. Across those five header variants, each of seven invalid raw inputs covering overprecision, overflowing or nonstandard numbers, and repeated members returned a serializable HTTP 422. `text/plain` with valid JSON returned 422. [Probe](evidence/review-initial-round-3-api.py) and [output](evidence/review-initial-round-3-api.txt).
- **PC-R07 resolved.** Unexpected nested arrays at 950 and 1,500 levels both returned serializable HTTP 422 in Python 3.9.4 and FastAPI 0.128.8. This exercises both typed validation and the decoder depth error. [API output](evidence/review-initial-round-3-api.txt).
- **PC-R01, PC-R02 and PC-R05 remain resolved.** Re-ran the live Chrome review probe with the repaired API. Committed allocations matched the 100.00% display and request, an invalid focused edit sent zero requests on Enter, and the guidance and keyboard outline exceeded their contrast thresholds. [Browser probe](evidence/review-initial-round-2-browser.py) and [output](evidence/review-initial-round-3-browser.txt).

### Finding

- **PC-R08, P3, blocking — AC-004. Invalid JSON string content can fail while rendering the validation response.** The decoder at `backend/src/api/controller/portfolio.py:77` accepts an escaped lone surrogate as a Python string. Submit the valid dates and one IFIX allocation of 100 with raw JSON `"rebalancing":"\ud800"` and `Content-Type: application/json`. The strategy fails validation at the handler reached from line 89. FastAPI's default error handler includes that string in its response, and Starlette raises `UnicodeEncodeError` when encoding the response as UTF-8. The observed status is HTTP 500. AC-004 requires HTTP 422 for invalid field values. A correction needs a serializable 422 for such rejected inputs at the request boundary. [Reproduction](evidence/review-initial-round-3-api.py) and [output](evidence/review-initial-round-3-api.txt).

### Checks and scope

- Reviewed the integrated diff including all four untracked implementation and test files. The index service and form, allocation arithmetic and locks, dates and strategy, pending and response states, accessible labels and layout, Vite proxies, manifests, and usage docs follow the approved boundaries. Changes contain no market data, acquisition or calculation code. The illustrative chart and health behavior remain covered by the existing tests.
- Ran `pnpm --dir frontend test` with 22 passing tests and the backend API and health suites in `backend/.venv` with 15 passing tests. `git diff --check` passed with line ending notices. [Frontend results](evidence/review-initial-round-3-frontend-tests.txt) and [backend results](evidence/review-initial-round-3-backend-tests.txt).
- Independent acceptance QA is pending. With the third initial round complete and PC-R08 open, the workflow calls for independent QA's available assessment before correction planning.

