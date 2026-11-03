# Verification

No implementation, TDD, review or QA has been performed.

## Discovery evidence — 2026-11-03

- The web reader returned no readable content for the requested IFIX page. A direct Python HTTPS request failed with Windows socket permission error 10013. Computer Use stopped because it could not determine the current browser URL reliably. These are environment/tool observations, not evidence that B3 is unavailable.
- An indexed [B3 daily-evolution page for another index](https://sistemaswebb3-listados.b3.com.br/indexStatisticsPage/daily-evolution/IBOVESPA?language=pt-br) shows year and semester selectors; this does not establish IFIX download mechanics.
- B3 [general terms](https://www.b3.com.br/main.jsp?doui_processActionId=setLocaleProcessAction&locale=pt_BR&lumA=1&lumII=8AE690F77A1A49BA017A5CE182412193&lumPageId=8AE690F77A1A49BA017A5CDEBBCF67BD) address usage of index data. Applicability to this specific operation is not established.

Source verification, TDD evidence and independent QA remain outstanding.

## Source inspection — 2026-11-03 (approved s001/p001)

Using an approved read-only network request, the requested page returned HTTP 200. Its own script `main-es2015.204ca04ae07d2c137636.js` at the page's origin generates year choices from 1998 through the current year, uses semester only to switch the displayed half-year, and sends `{index, language, year}` to `indexStatisticsProxy/IndexCall/GetDownloadPortfolioDay/<base64-json>`. Its download handler decodes the Base64 response and saves the resulting bytes as `Evolucao_Diaria.csv`; thus preserving the decoded bytes reproduces the actual downloaded file. This is the page's own endpoint, not an inferred third-party API.

For IFIX, pt-br, 2011 and 2026 the endpoint returned HTTP 200 text/plain Base64; decoded outputs begin with `IFIX - <year>` and a semicolon-delimited header containing all twelve months. The 2011 decoded file had 2,741 bytes, SHA-256 `8b338666afc34865d00af732898ea2cd58cdc1bc8b1fe535983fffe2bf4a8d20`, and populated cells from 2011-01-03 through 2011-12-29; the 2026 decoded file had 2,419 bytes, SHA-256 `48aed9dcc56b44d6b651a4bb20b937606919121ecddffbebb08835b6dcc1050f`, and populated cells through 2026-10-30. These are spot checks, not proof of all-year coverage or market completeness. UTF-8 decoding of the 2011 file failed; byte preservation is required. No files were saved to active data during inspection.

The separate `GetPortfolioDay` response was HTTP 200 JSON for both years. The requested page and script inspection did not establish an applicable prohibition on this specific operation; B3 general terms remain documented in discovery. The developer must report any actual restriction encountered, without bypass. Source behavior can change.

Baseline: HEAD `d9ac063dfb6abaa5f5a421cbf317a32e62dc39f6`; pre-existing worktree status comprised `M docs/agent-log/LOG.md` and untracked `docs/tasks/002-ifix-daily-evolution-acquisition/`. Snapshot: [baseline-snapshot.json](evidence/baseline-snapshot.json).

## Developer implementation evidence — 2026-11-03, s001/p001, initial round 1

Implementation: `backend/src/acquisition/ifix.py` uses Python standard library HTTPS with default certificate verification, 0.2-second request pacing, strict Base64 decoding and validation of the B3 IFIX annual CSV header. It checks years 2011 through the system current year, stores decoded original bytes, atomically updates a period-indexed manifest, preserves the active file when download or backup/replacement fails, and holds an exclusive lock. Recovery from a stale lock is manual and documented. No module import or application startup performs network access.

Test-first observations: the test module was written before the implementation. The initial test run before the module existed failed with `ModuleNotFoundError`, which was a setup failure and is not counted as behavioral red evidence. After creating an inert module skeleton, `test_years_cover_2011_through_current_year` failed because the function returned `[]` instead of 2011–2026; after implementation it passed. Later, `test_cli_reports_destination_errors_without_a_traceback` failed when an `OSError` escaped the command; catching destination errors made that regression test pass. `test_manifest_with_wrong_json_shape_fails_safely` failed with `AttributeError` for JSON `[]`; manifest type validation fixed it, and the test passed. The remaining implementation tests were authored before the implementation and passed in the integrated suite; no behavioral red failure was recorded for each of those individual cases. A test-only setup error (`FileExistsError` while creating an already-existing directory) was corrected in the test; it was not a product defect.

Verification commands (Windows, Python 3.9):

- `python -m unittest discover -s backend/tests -v` — passed, 16 tests. Includes Base64/source-year mapping, invalid payloads, partial failure, exact bytes and provenance, unchanged mtime, backup and restore bytes, backup/replacement failures, malformed manifest, overlapping lock, CLI help with no network, and destination errors. Controlled fixtures use explicitly non-market `TEST_FIXTURE_*` bytes.
- `python -m compileall -q backend` — passed. Generated bytecode caches were removed.
- `python -m backend.src.acquisition.ifix --help` — passed; printed command options and exited without network access.
- Source-backed integration smoke in a temporary directory: `IfixAcquisition(B3IfixClient(), FileStore(temp/data), current_year=2026).run()` — complete; saved 16/16 years (2011–2026), no updates, no unchanged files and no errors; manifest covered all 16 years. The temporary directory was automatically removed. No data files were added to the repository. This is developer evidence; independent QA remains required.
- Read-through confirmed the updated root, backend, acquisition and data instructions give the command, output paths, provenance, incomplete-run behavior and restore/stale-lock procedure.

Limitations: no automated restore command is provided; restoration is a documented file copy after stopping acquisition and checking the backup digest. The command queries every historical year on each run to detect B3 changes. B3 terms can change; no page-specific access restriction was observed during source inspection, but the user's personal-use purpose does not grant a license.

## Initial cycle, round 2 repair evidence — 2026-11-03, s001/p001

The implementation now follows the approved module boundaries: `acquisition/ifix_source.py` owns the B3 protocol and annual matrix validation, `application/ifix_acquisition.py` coordinates periods and outcomes, and `storage/ifix.py` owns the manifest, locking, backups, atomic updates, crash recovery and offline restore. `acquisition/ifix.py` only assembles the explicit CLI. Python standard library only; imports make no requests.

### Regression red/green evidence

- **RF-001:** wrote `test_client_rejects_truncated_annual_matrix`. After correcting the test opener to accept the client's `timeout=` keyword, it failed before the fix with `AssertionError: DownloadError not raised` for the review's truncated two-column row. The source adapter now requires the complete annual matrix (year and month headers, 31 ordered day rows of 13 columns, two summary rows) and at least one observation. The corrected test passes. `test_client_accepts_partial_current_year_with_blank_future_months` passes with the same 31-row matrix and blank future months. Live B3 2011 and 2026 files satisfy that structure.
- **RF-002:** wrote `test_manifest_write_interruption_keeps_backup_reference_for_rerun`. The pre-fix reproduction failed after simulating a manifest replacement error: rerun reported `unchanged` but `previous_versions` had length 0 although the backup existed. Storage now atomically records a pending update before replacing an active file, and reconciles it from old/new file hashes on the next operation. The passing regression verifies the rerun commits a valid backup path and digest. A mismatch preserves pending metadata and stops.
- **RF-003:** wrote `test_nested_manifest_record_is_rejected_before_active_replacement` for `files['2011'] = null` and `previous_versions = 'invalid'`. Before the fix, the null case raised `AttributeError` only after the active bytes changed, while the malformed list case was accepted. Storage now validates nested file and backup records before mutation; both subcases pass and the old active bytes remain unchanged.
- **RF-004:** expanded `test_offline_restore_command_is_available_without_downloading` to create old/new fixture files, then run the restore CLI. Before the fix, argparse rejected the `restore` operation with exit code 2. The passing test confirms restore makes no B3 call, verifies the listed backup hash, atomically restores the old bytes, records restore provenance, and saves the displaced new bytes as a recoverable backup. Documentation gives the offline command and warns that a future explicit download can refresh the restored version.
- Additional regression `test_restore_cli_reports_invalid_year_as_a_command_error` failed before its fix with an uncaught `ValueError` for year 2010; it now returns a concise command error and nonzero exit.

A mock signature in two original source tests did not accept the keyword `timeout`; their earlier apparent passes were wrapped `TypeError`s and are not behavioral evidence. I corrected the test callbacks, then ran RF-001's true behavioral red before its source-validation fix. The original RF-005 limitation remains as recorded; no missing earlier TDD results have been reconstructed.

### Round 2 checks

- `python -B -m unittest discover -s backend/tests -v` — passed, 22 tests.
- `python -B -m compileall -q backend` — passed; generated caches removed.
- `python -B -m backend.src.acquisition.ifix --help` — passed without network access.
- `python -B -m backend.src.acquisition.ifix restore --help` — passed; exposes year and manifest-relative backup arguments.
- Live CLI smoke: `python -m backend.src.acquisition.ifix --data-dir <temporary-data-dir>` with B3 reachable — exit 0; 16 files saved for 2011–2026; manifest covered all 16 years; no errors. The temporary directory was automatically removed and no B3 data was saved in the repository.
- Documentation review: root README, acquisition, application and storage guidance, data README and project context now describe the implemented boundary, backup/restore and no-network-on-import behavior. Project context retains all open financial-convention decisions.

Independent round-2 review and QA remain outstanding.

## Independent QA — 2026-11-03, s001/p001, reviewed snapshot `f0e6c7622a274e0ed439dfd6d523e7591abb0b08:sha256:a130928277e0cc11c444d8e0cbc15d2b3a8a0c0be35d6cda56bde9ad35f10420`

Environment: Windows, Python 3.9. QA snapshot before and after is identical: [before](evidence/qa-initial-2-before.json), [after](evidence/qa-initial-2-after.json). All downloaded source files were written under OS temporary directories and removed on exit. No active B3 data was added to the repository.

### Acceptance matrix

- **AC-001 — pass.** Expected: explicit command performs the run; help/import do not start data acquisition. Actual: the explicit `python -B -m backend.src.acquisition.ifix --data-dir <temporary-data-dir>` completed live; `--help` returned 0 without requesting data; reviewed module import and CLI assembly contain no call on import/startup.
- **AC-002 — pass.** Expected: distinct year-labelled files preserve downloaded bytes and the manifest hashes/source details. Actual: CLI saved 16 annual files for 2011–2026. Independently queried B3's own annual download response for 2011 and current/latest 2026, Base64-decoded the same way as the site page, and compared every byte to the corresponding saved file and manifest hash. Both matched: 2011, 2,741 bytes, SHA-256 `8b338666afc34865d00af732898ea2cd58cdc1bc8b1fe535983fffe2bf4a8d20`; 2026, 2,419 bytes, SHA-256 `48aed9dcc56b44d6b651a4bb20b937606919121ecddffbebb08835b6dcc1050f`. The 2026 file has observations through 2026-10-30, with later months blank. The files use the fixed twelve-month annual layout.
- **AC-003 — pass.** Expected: complete coverage succeeds; a period, discovery, invalid response or write failure is visible and cannot masquerade as complete. Actual: full live run exited 0 with saved years 2011–2026 and no errors. The independent 22-test run passed cases for partial source failure, no available years, invalid Base64/wrong period, truncated CSV, and destination errors. It reports `complete=False` for partial/no-period outcomes.
- **AC-004 — pass.** Expected: unchanged data creates no backup, keeps timestamps, and changed data remains recoverable through failure or restore. Actual: a second independent live run reported all 16 years unchanged, preserved each file's `mtime_ns`, and left backup lists empty. The 22-test suite passed backup failure, replacement failure, interrupted manifest-write recovery, backup digest validation, and restore coverage. An independent temporary fixture integration restored old bytes through the offline CLI, verified restore provenance, saved the displaced current bytes as a second backup, and patched any B3 call to fail; restore still succeeded without network access. Malformed nested-manifest testing left active bytes unchanged.
- **AC-005 — pass.** Expected: source, orchestration and storage responsibilities are separated, and overlapping work fails without mutation. Actual: the inspected modules are `acquisition/ifix_source.py`, `application/ifix_acquisition.py`, and `storage/ifix.py`, with `acquisition/ifix.py` as explicit command assembly. The 22-test suite passed lock exclusion; a separate CLI check with a held lock returned 1 and made no request or active directory.
- **AC-006 — pass with a recorded nonblocking process limitation.** Expected: meaningful adverse tests and use/restore documentation. Actual: `python -B -m unittest discover -s backend/tests -v` passed all 22 tests independently; CLI and offline restore help returned 0; every Python source parsed successfully. Reviewed root/backend/application/acquisition/storage/data and project-context documentation for paths, commands, provenance, incomplete runs, backups and offline restore. Round-2 regression reds were recorded for all four original review defects. **RF-005 remains open:** not every first-round test had an observed behavioral red before implementation. The developer recorded this honestly, and QA does not infer full test-first evidence from passing tests. This is a workflow evidence limitation, not a failed product behavior; it needs explicit lead disposition and relevant human acceptance before final completion.
- **AC-007 — pass.** Expected: documented command and real source agree for the earliest requested and latest currently offered period. Actual: in addition to the source byte comparisons above, the independent live CLI reported all 16 years (2011–2026), including the latest current-year file; a second run found all unchanged. Both runs exited 0. Requests followed the page's own download flow; no access restriction was bypassed.

### QA commands and results

- `python -B -m unittest discover -s backend/tests -v` — 22 passed.
- `python -B -m backend.src.acquisition.ifix --help` — exit 0; no acquisition.
- `python -B -m backend.src.acquisition.ifix restore --help` — exit 0.
- AST parse of all backend `*.py` files — passed.
- `python -B -m backend.src.acquisition.ifix --data-dir <temporary-data-dir>` — live B3 run, exit 0, all 16 years saved. Repeat — exit 0, all 16 unchanged. Temporary data automatically removed.
- Direct source equivalence checks for 2011 and 2026 — each HTTP 200, B3 Base64 response decoded, bytes and SHA-256 matched saved file and manifest.
- Independent temporary adverse scenarios — verified offline backup restore, preservation of displaced bytes, restore without network, rejection of existing lock, and malformed nested manifest with unchanged active bytes.

No project UI exists for this command-line feature, so browser UI testing is not applicable. No implementation defect or ambiguous approved convention remains from QA. The historical TDD evidence limitation and the general B3 terms' applicability (not established by these checks) are recorded separately.

## Project acquisition — 2026-11-03

Ran `python -B -m backend.src.acquisition.ifix` from the project root with approved network access. Exit 0: saved all 16 files for 2011–2026, no updates or unchanged files. This populated the project data directory after independent QA had used a temporary directory. Snapshot: [acquired-data-snapshot.json](evidence/acquired-data-snapshot.json). Because the working-tree snapshot now includes the acquired data, independent review and affected QA are refreshed on that snapshot.

## QA refresh after project data acquisition — 2026-11-03, s001/p001, snapshot `f0e6c7622a274e0ed439dfd6d523e7591abb0b08:sha256:fe8395f944e4b0e1d7c652138b00d1fb5045ebeb18c60f0d922eba67603c2c4c`

The repository now contains the user's requested acquired IFIX files in `data/ifix/source/`. The implementation and prior independent evaluation snapshot is `f0e6c7622a274e0ed439dfd6d523e7591abb0b08:sha256:a130928277e0cc11c444d8e0cbc15d2b3a8a0c0be35d6cda56bde9ad35f10420`. An impact comparison showed exactly 17 changed paths: `data/ifix/manifest.json` and the 16 annual source CSVs for 2011–2026. Application code, tests, configuration and documentation are unchanged. Therefore the prior independent 22-test run, error/restore/lock scenarios, CLI checks and documentation evaluation remain valid for this snapshot. They are linked above rather than rerun against the actual data directory.

Read-only check of the acquired project data: there are exactly 16 active `.csv` files, one for each year 2011–2026; the manifest contains those same periods; each active file passes the source structure validator and its SHA-256 matches its manifest record. Independently requested the current B3 export for the earliest period 2011 and latest available year 2026. Both HTTP 200 responses decoded to bytes exactly equal to their project files and manifest hashes (2011: 2,741 bytes, `8b338666afc34865d00af732898ea2cd58cdc1bc8b1fe535983fffe2bf4a8d20`; 2026: 2,419 bytes, `48aed9dcc56b44d6b651a4bb20b937606919121ecddffbebb08835b6dcc1050f`). No files were written or changed during this refresh.

Expected: complete project data from 2011 through the latest B3 year with exact source bytes and matching provenance. Actual: 2011–2026, 16 files; all 16 validate and match manifest digests, and the two boundary-year files match B3 directly. The current-year file contains data through 2026-10-30. Snapshot before and after this read-only evaluation matches: [before](evidence/qa-acquired-data-before.json), [after](evidence/qa-acquired-data-after.json). Changed-path and reuse rationale: [impact record](evidence/qa-acquired-data-impact.json).

Acceptance results are refreshed to the acquired-data snapshot; AC-002 and AC-007 now include direct evidence about the project files. All AC-001–AC-007 remain passed with the documented reuse rationale. RF-005 remains a nonblocking historical test-first evidence limitation; it still needs lead disposition and relevant human acceptance.

## Lead final audit — 2026-11-03

Verified exact approved specification and plan hashes, current snapshot identity against passed review and QA, all seven acceptance results passed against the same snapshot, no unresolved blocking findings, and no active assignments. Snapshot: [final-audit-snapshot.json](evidence/final-audit-snapshot.json). The 22-test suite, live B3 file comparisons, restore and adverse-case checks are recorded above. The acquired project files are included in this snapshot. RF-005 remains an explicitly disclosed, nonblocking process-evidence limitation pending human acceptance; unobserved test-first history cannot be reconstructed.
