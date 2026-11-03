# Verification

## Implementation handoff — s001/p001, initial round 1

The developer integrated the Selic getter and offline tests. Full acceptance and live-source evidence remain incomplete because the isolated Playwright run returns a date range different from the requested range; no project Selic CSV was written.

### Observed TDD

- **AC-001 registry:** `test_selic_is_registered_as_an_explicit_getter` first failed with `AssertionError: 'selic' not found in ('ifix',)`. After adding `selic` to the registry it passed.
- **AC-002/AC-003 page verification:** the fake browser-flow test first failed because the proposed result-period check read the values table rather than BCB's search-parameters table. The check was changed to verify the period/function in `#seriesSelecionadas`; it passed.
- **AC-002 refresh ordering:** the fake browser-flow test was tightened to require the chart image before opening values. It failed with `values opened before the refreshed chart finished loading`. The client now waits for the chart image to be visible and loaded before clicking “View values from chart”; the fake browser-flow test passes. Live range mismatch persists after that wait.
- **AC-003 pagination link selection:** the fake browser test exposed that BCB renders a `Next` link at both the top and bottom of the table. The unqualified click failed the fixture's strict ambiguity check; the client now selects the first link, and the page-through test passes.
- **Restore decimal parsing:** the offline restore test exposed that the BCB page uses a comma decimal while the generated CSV uses a period; restore incorrectly ran source parsing against the CSV. Restore now validates period-decimal CSV text directly and the test passes.
- Parser, store, and other tests were added after their corresponding first-pass implementation and initially passed. They do not supply observed test-first red evidence; this process limitation is explicit.

### Checks run

Using `backend/.venv` (Python 3.9, Playwright 1.60.0):

- `python -m unittest discover -s backend/src/internet_data_getter/tests -v` — 40 tests passed.
- `python -m backend.src.internet_data_getter --help` — passed; lists `ifix`, `selic`, `restore`, and `restore-selic` without a source request.
- `python -m compileall -q backend` — passed.
- `python .agents/skills/feature-workflow/scripts/snapshot.py --root .` — snapshot in `evidence/implementation-round-1-snapshot.json`.

### Live-source discrepancy (unresolved)

- An isolated Playwright Chromium run opened the specified SGS chart, read latest source date `30/10/2026`, filled `01/01/2011` and `30/10/2026`, clicked Refresh chart, waited for the refreshed image, clicked View values from chart, and observed the result parameters `03/11/2016 to 03/11/2026`; BCB reported 2,508 rows. The client rejects this mismatch as incomplete. The reproduction/debug script is `evidence/inspect_bcb_page.py`.
- In Chrome, using the visible controls (`dataInicio=01/01/2011`, `dataFim=30/10/2026`, Refresh chart, View values from chart), the values page showed `01/01/2011 to 30/10/2026`, 3,976 rows and 40 pages. The first displayed rows were 03/01/2011 `0,040239`, 04/01/2011 `0,040203`.
- The disagreement is reproducible between the isolated CLI browser and the interactive Chrome session. No result is being treated as complete and the project `data/selic/` directory has not been created or written.

### Limits at handoff

The pure parsing/storage tests pass, but the CLI has not completed an actual full-range scrape. Acceptance criteria AC-002, AC-003 and AC-007 remain unverified/blocked. Review and independent QA have not occurred. Live project-data acquisition is not attempted. The user-visible output schema, backup paths, usage terms and restore behavior need independent review against s001/p001 after the browser mismatch is resolved.

## Implementation handoff — s001/p001, initial round 2

Repaired RF-001 through RF-007 from the round-1 review. This is developer evidence only; independent review and QA remain outstanding. No CSV was acquired into project `data/`.

### Observed TDD and review repairs

Regression tests are in `backend/src/internet_data_getter/tests/test_selic_acquisition.py`. Targeted runs used `backend/.venv/Scripts/python.exe -m unittest backend.src.internet_data_getter.tests.test_selic_acquisition.SelicRegistryTests.<test_name> -v`; the same targeted tests were rerun after each fix to observe green results.

- **RF-001, AC-002/AC-003/AC-007 — chart refresh synchronization:** `test_browser_client_sets_source_range_refreshes_opens_values_and_pages` failed before the source change with `refresh clicked before static chart iframe form attached`. The client now waits for the iframe form and the `atualizarGraficoEstatico` POST response, checks its HTTP status, and only then reads the refreshed chart and opens values. The live trace recorded the exact filters `01/01/2011` and `30/10/2026`, a refresh POST with status 200, and the expected refreshed period.
- **RF-002, AC-004/AC-005 — ambiguous recovery:** `test_recovery_preserves_unknown_manifest_and_pending_record` failed before the repair because recovery did not raise after the manifest was replaced with unrelated bytes; the prior code overwrote those bytes and deleted the pending record. Recovery now validates active CSV and manifest hashes as a pair, recognizes committed, old and already-rolled-back states, and preserves the manifest and pending record for unknown states. The regression passes with both bytes unchanged. `test_recovery_recognizes_an_already_written_rollback_manifest` also passes after an injected interruption between rollback-manifest replacement and pending-record removal.
- **RF-003, AC-004/AC-005 — recursive history:** `test_repeated_updates_keep_current_manifest_history_flat` first failed with a current manifest of 715,714 bytes after ten fixture updates (the test limit is 20,000 bytes). Backup references now contain only paired paths and hashes; the historical paired manifest retains each version's source metadata. The ten-update regression passes below the size limit.
- **RF-004, AC-004/AC-005 — offline restore provenance:** `test_restore_preserves_source_retrieval_time_and_records_local_restore_time` first failed because the restored record claimed `2026-02-11T00:00:00Z` as its retrieval time instead of the original `2026-02-01T00:00:00Z`. Restore now uses the hash-verified paired historical manifest, preserves `retrieved_at`, and records the local restore operation as `restored_at`. The test passes.
- **RF-005, AC-002/AC-003 — exact series identity:** `test_values_page_rejects_series_code_lookalikes_in_metadata_and_header` first failed because both `111 - Interest rate - Selic` plus date `11/02/2011` and a `111 % p.d.` column header were accepted. After adding a positive case for the exact observed BCB layout, `test_values_page_checks_exact_series_code_in_metadata_and_header` failed because the landing page presents `11<TAB>Interest rate - Selic` inside a table after “Found series”. The client now locates one exact code-11 series entry in the metadata, supports both BCB metadata layouts, and checks the exact `% p.d.` data-column header on the first values page. Both adversarial and valid-layout cases pass.
- **RF-006, AC-003 — count and pagination end:** the nonfinal-page case in `test_browser_client_sets_source_range_refreshes_opens_values_and_pages` first failed with `SourceError not raised` when the expected count was reached but `Next` remained available. The client now checks pagination end and count together, rejects repeated pages, and rejects a count reached while `Next` still exists. The combined regression passes for nonfinal, repeated-page and premature-end cases. A further red from the same browser test reported `Next clicked without waiting for the page transition`; a live probe confirmed BCB sends `POST method=getPagina`. The client now awaits that response and `DOMContentLoaded` before reading the next page.
- **RF-007, AC-006 — controlled fixture observations:** this is a fixture-content correction, so an executable red step does not apply. Offline observations now use controlled decimal markers such as `0.123456`, `0.123400`, `0.050001` and `0.060002`; the observed BCB January 2011 values remain only in live-source evidence, not test fixtures. The exact CSV fixture assertion passes.
- **RF-008 process limitation:** retained from round 1. Some initial tests were written after their implementations, so those historical pre-implementation reds were not observed and are not reconstructed. Round-2 findings above have their actual observed red results recorded.

### Refactor and checks

Storage now shares paired-backup creation and atomic transaction commit logic between acquisition and restore; flat references are normalized when saving and recovering legacy records. The source adapter has a single exact-series identity check and explicit response/navigation waits. These changes passed the same regressions and the full suite.

Using `backend/.venv` (Python 3.9, Playwright 1.60.0):

- `backend/.venv/Scripts/python.exe -m unittest discover -s backend/src/internet_data_getter/tests -v` — 45 tests passed.
- `backend/.venv/Scripts/python.exe -m backend.src.internet_data_getter --help` — passed; help lists `selic`, `restore` and `restore-selic` without a source request.
- `backend/.venv/Scripts/python.exe -m compileall -q backend` — passed.
- `git diff --check` — passed; Git emitted line-ending normalization warnings for existing Markdown files only.
- `evidence/implementation-round-2-live-smoke.py` — complete live scrape passed in a temporary directory: 3,976 observations, `2011-01-03` through `2026-10-30`, CSV SHA-256 `21e0e6a98aebd0b27f8c9d7f7b07f37d0bffe9d0d96ff85ebda20319d23c6a6f`. It observed the refreshed range and traversed the reported pages. The temporary directory was removed after the run; `data/selic/source/selic_sgs_11.csv` was not created.
- Integrated snapshot: see `evidence/implementation-round-2-snapshot.json`.

The implementation is ready for independent review on the snapshot above. No review or QA verdict is claimed here; project-data acquisition remains for the lead's post-QA plan.

## Implementation handoff — s001/p001, initial round 3

Repaired RF-009 and RF-010 on the approved revisions. The round-2 live smoke remains evidence for the source path; this pass made offline validation changes only and did not run another live scrape or write project data.

### Observed TDD

Regression tests are in `backend/src/internet_data_getter/tests/test_selic_acquisition.py`. Targeted runs used `backend/.venv/Scripts/python.exe -m unittest backend.src.internet_data_getter.tests.test_selic_acquisition.SelicRegistryTests.<test_name> -v`.

- **RF-009, AC-004/AC-005 — validate required provenance:** `test_unchanged_save_rejects_corrupt_provenance_and_preserves_files` first failed with `ManifestError not raised` after removing the manifest unit, clearing `retrieved_at`, and setting the observation count to 99 for unchanged bytes. `test_unchanged_save_rejects_counts_that_disagree_with_the_csv` also failed with `ManifestError not raised` when both manifest counts were changed to 99 while the CSV still held two rows. The store now requires source URL/dataset/code, unit/license, canonical retrieval time, format, requested/observed coverage, counts and hash; it parses the paired CSV and verifies its bytes, count and date coverage before unchanged success. It performs the same pair checks on known recovery states and before using current or historical manifests for restore. Both regressions pass, with the corrupt active CSV and manifest preserved byte-for-byte.
- **RF-010, AC-003/AC-006 — fail closed on malformed observation rows:** `test_parser_rejects_a_malformed_date_with_numeric_rate` first failed with `SourceError not raised` for a table containing valid endpoints and a numeric-rate row dated `03-02-2011`. The parser now recognizes malformed date-like fields and rejects them, including numeric-rate rows with an empty or malformed date, while continuing to skip headers, pagination and source footer rows. The regression passes; the remaining parser and browser fixtures pass.

### Checks and limits

- `backend/.venv/Scripts/python.exe -m unittest discover -s backend/src/internet_data_getter/tests -v` — 48 tests passed.
- `backend/.venv/Scripts/python.exe -m compileall -q backend` — passed.
- `git diff --check` — passed with line-ending normalization warnings only.
- No project Selic data was acquired. Round-2 live-smoke evidence remains tied to its prior snapshot; live QA and project acquisition are still outstanding.
- Integrated round-3 snapshot: see `evidence/implementation-round-3-snapshot.json`.

Developer implementation handoff only. Independent review remains required on the new snapshot.

## Independent QA — initial cycle round 3, s001/p001

QA evaluated code snapshot `f218c35e050e196a47e724ee348def9035671601:sha256:fc8f20234e69450785184f5d7af3a56769108c320d56aa7fd7cb875ade042192`. Before and after code snapshots match; see `evidence/qa-initial-3-before.json` and `evidence/qa-initial-3-after.json`. Environment: Windows, Python 3.9 in `backend/.venv`, Playwright 1.60.0 with Chromium, direct BCB page in Chrome, and temporary data output under `%TEMP%`.

| Criterion | Result | Expected and observed |
| --- | --- | --- |
| AC-001 | Pass | CLI help ran without a request; suite includes no-network import/help checks. Explicit `--getter selic` selected only Selic and produced the complete run report. |
| AC-002 | Pass | Direct chart query used `dataInicio=01/01/2011` and chart-reported latest `dataFim=03/11/2026`, Linear function. Result confirmed series 11, Selic, `% p.d.`, requested period, and latest date. |
| AC-003 | Pass | Direct values view reported 3,977 observations and 40 pages. The temporary CLI completed all pages with 3,977 rows from 2011-01-03 through 2026-11-03. First, middle (page 20) and last (page 40) source samples match the CSV. |
| AC-004 | Pass | Temporary UTF-8 CSV had exact headers, ISO dates and preserved decimal precision. Manifest count/date coverage/hash/unit and ODbL statement matched. Second live invocation returned `unchanged` with identical SHA-256 and no Selic backup. Offline tests passed changed-save, verified backup, restore provenance and recovery cases. |
| AC-005 | Pass | Offline tests passed overlapping-lock rejection, failed atomic write, pending recovery, unknown manifest preservation, rollback recovery and hash-verified restore checks. |
| AC-006 | Pass | `python -m unittest discover -s backend/src/internet_data_getter/tests -v`: 48 tests passed. These include malformed date/rate, identity lookalikes, changed period/function, wrong counts/order/latest date, pagination, source denial, corrupt provenance, changed/unchanged storage, recovery, restore and concurrency. `compileall` and `git diff --check` also passed. Git emitted LF-to-CRLF normalization warnings for Markdown files. |
| AC-007 | Blocked pending lead action | Live BCB browser and full documented CLI were independently exercised successfully; detailed output, time-varying count and three source/CSV comparisons are in `evidence/qa-initial-3-live-cli.txt`. This QA assignment prohibited writing project data. The specification also requires a post-check run into the project data directory and validation there. `data/selic/source/selic_sgs_11.csv` and its project manifest are currently absent; the lead must perform that authorized acquisition and arrange QA evidence on the resulting data snapshot. |

### Live source actions and observations

The existing Chrome BCB tab initially displayed an expired session notice. After reloading the requested chart page, QA set the two filters, clicked `Refresh chart`, then `View values from chart`. BCB displayed latest observation 03/11/2026, the refreshed chart, the requested result range, 3,977 observations, and a 40-page pagination control. QA navigated to `Last` (page 40) and then `-10` twice to page 20. Direct BCB observations matched the generated CSV: 03/01/2011 `0,040239` vs. `2011-01-03,0.040239`; 28/09/2018 `0,024620` vs. `2018-09-28,0.024620`; 03/11/2026 `0,050788` vs. `2026-11-03,0.050788`.

The first CLI attempt in the default sandbox returned `net::ERR_NETWORK_ACCESS_DENIED` and produced no complete file. With approved elevated network access, the same documented command in the temporary folder completed (`saved`, 3,977 rows, hash `b9f3d96ac8504f77bcc08fdbe3024eb2e760c9e8190a8fba726a20ad79414688`). A second run returned `unchanged` and the same hash. The temporary CSV and manifest were validated and no project data files were written.

The source values and observation count can change as BCB publishes new observations; this run's latest value date was 2026-11-03. QA did not treat that date or count as fixed expectations. RF-008 remains an open nonblocking process-evidence limitation: initial-round tests added after implementation do not have observed historical reds, and that history is not reconstructable.


## Project-data acquisition — post-QA action for AC-004 and AC-007

Executed the approved planned acquisition on code snapshot `f218c35e050e196a47e724ee348def9035671601:sha256:fc8f20234e69450785184f5d7af3a56769108c320d56aa7fd7cb875ade042192`, using the documented command:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --data-dir data --getter selic
```

The default sandbox attempt exited 1 before receiving source data (`net::ERR_NETWORK_ACCESS_DENIED` at the BCB SGS 11 chart; 0 observations). Retried the same command with approved elevated network access. It exited 0 and reported `saved`, 3,977 observations, coverage `2011-01-03` through `2026-11-03`, and CSV SHA-256 `b9f3d96ac8504f77bcc08fdbe3024eb2e760c9e8190a8fba726a20ad79414688`. The manifest records retrieval time `2026-11-03T21:42:42Z`, requested start `2011-01-01`, source-reported requested end `2026-11-03`, the 3,977 reported/acquired counts, `% p.d.`, series 11, source and dataset URLs, and BCB's listed ODbL license.

Validated the project CSV and matching manifest in place. The 79,566-byte UTF-8 CSV has the exact `date,rate_percent_per_day` header, 3,977 unique increasing ISO dates, decimal text values, and coverage matching the manifest. Its SHA-256 matches the manifest. All acquisition validation checks passed; no previous-version backup, pending transaction, or lock remained after this first save. The first, middle and last values match the independently browsed BCB rows recorded in `evidence/qa-initial-3-live-cli.txt`: `2011-01-03,0.040239`, `2018-09-28,0.024620`, and `2026-11-03,0.050788`.

Post-acquisition workspace snapshot: `f218c35e050e196a47e724ee348def9035671601:sha256:0979d83d473acf782bdebe9332592698aa65e0b2509d1a0e66ba00b8a5adbdf1` (see `evidence/project-data-acquisition-after.json`). The snapshot includes the active CSV and manifest; application code is unchanged.

Evidence: `evidence/project-data-acquisition-before.json`, `evidence/project-data-acquisition-validation.json`, and `evidence/project-data-acquisition-after.json`. No application code, tests or durable product documentation were changed for this acquisition. This records the planned project-data action; independent review/QA refresh on the resulting data snapshot remains for the lead to arrange.

## Independent QA refresh — acquired project data, s001/p001

QA refreshed the acceptance record on current snapshot `f218c35e050e196a47e724ee348def9035671601:sha256:0979d83d473acf782bdebe9332592698aa65e0b2509d1a0e66ba00b8a5adbdf1`. The before and after evaluation snapshots match; see `evidence/qa-acquired-data-before.json` and `evidence/qa-acquired-data-after.json`. The impact comparison `evidence/qa-acquired-data-impact.json` shows the only changes since the prior QA code snapshot are `data/selic/manifest.json` and `data/selic/source/selic_sgs_11.csv`. No code, tests, configuration or durable documentation changed. Therefore prior QA results for AC-001–AC-006 and live-browser actions remain applicable; this refresh independently revalidated the project artifacts and AC-007.

| Criterion | Current result | Expected and actual behavior |
| --- | --- | --- |
| AC-001 | Pass; prior QA reused with impact reasoning | Explicit getter and no-network import/help checks passed on unchanged implementation. |
| AC-002 | Pass; prior QA reused with impact reasoning | BCB browser query selected series 11, daily `% p.d.`, Linear, 2011-01-01 through source latest 2026-11-03. |
| AC-003 | Pass; prior QA reused with impact reasoning | All 3,977 reported rows across 40 pages were present in the acquired CSV; dates increase uniquely from 2011-01-03 to 2026-11-03. Independent browser samples from pages 1, 20 and 40 match. |
| AC-004 | Pass; project artifacts revalidated | The project CSV's SHA-256 is `b9f3d96ac8504f77bcc08fdbe3024eb2e760c9e8190a8fba726a20ad79414688`, matching the manifest; both reported and acquired counts are 3,977 and coverage matches. The file has the required UTF-8 header and decimal-point values. The manifest records source URLs, series, unit, ODbL statement and retrieval time. Prior unchanged/backup/recovery tests remain applicable because code is unchanged. |
| AC-005 | Pass; prior QA reused with impact reasoning | Locking, safe replacement, recovery and offline restore tests passed for unchanged implementation; acquired data is outside backup inputs and has no pending transaction or lock. |
| AC-006 | Pass; prior QA reused with impact reasoning | 48 tests, CLI help, compileall and diff check passed on unchanged implementation. RF-008 remains a recorded nonblocking process-evidence limitation for lead disposition. |
| AC-007 | Pass | The approved documented acquisition wrote project CSV and manifest. Read-only validation independently confirmed count, coverage, hash, format, unit and provenance. Sample values matched the direct BCB rows already observed during browser QA: 2011-01-03 `0.040239`, 2018-09-28 `0.024620`, 2026-11-03 `0.050788`. Detailed machine-readable output is `evidence/qa-acquired-data-validation.json`; its script is `evidence/qa-acquired-data-validation.py`. |

QA executed only read operations against the project CSV and manifest. The acquisition remains tied to retrieval time `2026-11-03T21:42:42Z`; counts and latest dates may advance on future explicit runs. No acceptance criterion remains blocked on the current snapshot.

## Lead final evidence audit — 2026-11-03

Approved s001/p001 hashes remain unchanged. All seven acceptance results pass on the current snapshot, independent review and QA passed with matching before/after snapshots, no blocking findings or active assignments remain, and the final audit snapshot matches the evaluated revision (`evidence/final-audit-snapshot.json`). Documentation and the user-requested project dataset are present. RF-008 remains a nonblocking process-evidence limitation: some initial tests lacked observed pre-implementation reds. These cannot be reconstructed; each confirmed behavioral repair used a recorded failing regression, and independent review, QA, 48 tests and live source comparisons passed. Explicit human acceptance of this limitation is requested with final approval.
