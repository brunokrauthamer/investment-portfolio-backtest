# Verification

## Initial implementation source gate — 2026-11-03

Approved inputs: spec s001 (`200cc807b4caf05b77e93db405fef6ac4d20dc0f84f2c222f4283774faddb1cc`) and plan p001 (`70ac5abe315854f4405cd3e59381442972de250614b1b9e230d244991a06cbf4`). The first inspection attempt did not establish the export response; the environment blocker was later resolved using permitted direct HTTPS, as recorded below.

Observed in the requested B3 page in Chrome at `https://sistemaswebb3-listados.b3.com.br/indexStatisticsPage/daily-evolution/IBOV?language=pt-br`: year selector displayed 2011–2026; selecting 2011 changed the heading to “IBovespa - 2011” and showed the annual matrix with day rows, Portuguese month headings and MÍNIMO/MÁXIMO rows. The visible selected-year download link pointed to `/indexStatisticsPage/daily-evolution/IBOV/daily-evolution/IBOVESPA`. The page also stated that IBOV daily closing points are shown since January 1988. These UI observations establish the selected-year controls, visible table and anchor only; they do not establish file bytes, response content type, original filename/extension, encoding, download transport or the endpoint's relationship to the IFIX endpoint. The page's accessibility tree did not expose the export response.

Initial access attempts and outcomes: the web reader returned zero readable lines; direct `urllib` to the requested HTTPS page failed with Windows `WinError 10013` (socket access denied); browser policy rejected `chrome://downloads` and explicitly prohibited using another browser surface, raw CDP or browser commands to reach the same information. No restricted browser surface was used after that policy response.

### Source inspection continuation

On 2026-11-03, the lead confirmed that sandbox networking had been enabled for direct B3 HTTPS and supplied the successful proxy request shape. I independently repeated read-only requests using the IFIX `GetDownloadPortfolioDay` route with `index=IBOV`, `language=pt-br`, and years `2011` and `2026`, with the requested B3 page as Referer. Both returned HTTP 200 and `text/plain; charset=utf-8`; response bodies were valid Base64. Decoded byte lengths were 3,052 and 2,875, with SHA-256 `c232d0921337496042d9241f7ac0a78db625b6c9de0eb0ca31e69aa4da41df9f` and `74f1046d61fc6011cbf0ff62873a9475435778a1247ecc3e8b1e0aeedb9450b9`, respectively. Both decode as CP1252, each has 35 nonempty semicolon-delimited rows: `IBOV - <year>`, the 12 Portuguese month headings, 31 rows of 13 columns, and two 13-column nonnumeric summary rows. At least one daily observation exists in each response. The source returned the summary label `MÍNIMO` on both summary rows; observed page structure shows minimum and maximum rows, so validation will match IFIX's structural check (complete width, nonnumeric labels) rather than inventing an unobserved distinct-label requirement.

The visible page selector showed all years 2011–2026 at inspection time; the page table heading and values changed to `IBovespa - 2011` when 2011 was selected. The page's visible download anchor `/indexStatisticsPage/daily-evolution/IBOV/daily-evolution/IBOVESPA` independently returned HTTP 200 HTML when fetched directly without page interaction, not the CSV. The public page's `main-es2015.204ca04ae07d2c137636.js` static asset (HTTP 200, 543,553 bytes) shows the selected-page component calling `downloadFile(this.filterService)` and `saveAs(e,"Evolucao_Diaria.csv")`; its `main-es5.204ca04ae07d2c137636.js` fallback (HTTP 200, 625,297 bytes) contains the same download filename. Both assets call `GetDownloadPortfolioDay/` with Base64-encoded JSON. This verifies `Evolucao_Diaria.csv` as the user-visible original download filename. The implemented stable active name adds `IBOVESPA` and year while the manifest retains this verified source filename. The proxy response itself has no `Content-Disposition` filename header. The user-visible anchor route is not treated as a direct file endpoint.

This source evidence resolves the earlier source-access blocker sufficiently to proceed with implementation under s001/p001. It establishes the years 2011 and 2026, response transport, encoding, shape and original filename; it does not constitute independent QA of the integrated command or a complete-year range check. Automated tests and live QA remain pending. No historical observations were written to the repository during this inspection. Structured source evidence is in `evidence/source-inspection.json`.

## Initial implementation round 1

### Test-first evidence

- **Observed red — AC-001/AC-003 source and entry point:** Before adding the IBOVESPA package, ran `backend/.venv/Scripts/python.exe -m unittest backend.src.internet_data_getter.tests.test_ibovespa_acquisition backend.src.internet_data_getter.tests.test_getter_public -v`. It ran 9 tests; the new source test module failed import with `ModuleNotFoundError: No module named 'backend.src.internet_data_getter.ibovespa'`, and the two public-entry tests failed with `ImportError: cannot import name 'acquire_ibovespa'`. Existing getter tests passed. These failures were observed before implementing the source package and registry entry.
- **Green — AC-001/AC-003:** After adding the source client and registry/export, reran the same command: 13 tests passed. These tests verified year selection, `IBOV` Base64 request construction and unchanged decoded bytes, CSV shape validation, invalid Base64/year/index/truncation/no-observations, HTTP denial and pacing, public entry point, registry, and the selected shared CLI path.
- **Storage and service TDD limitation:** The later focused tests for safe storage, restore, recovery and service partial failures were added after the IFIX-aligned IBOVESPA module files had been copied. They passed, but no pre-implementation red result was observed for those behaviors. Do not treat them as test-first evidence.
- **Shared storage refactor:** To follow the repository guidance after the two B3 assets established a common safety requirement, the duplicate storage code was extracted into `backend/src/internet_data_getter/b3_storage.py`. Existing behavioral tests for both assets remained green, and each asset keeps a small `FileStore` configuration adapter.
- **Test fixture correction:** The first expanded run failed one new “incomplete summary” case because its byte replacement did not alter the fixture. The test now changes the final summary row by parsing/rebuilding the fixture; this was a test setup failure, not a production defect. The corrected test and full suite pass below.

### Observed checks

- `backend/.venv/Scripts/python.exe -m unittest discover -s backend/src/internet_data_getter/tests -v`: **51 tests passed**, including all existing IFIX tests and IBOVESPA tests for exact-byte storage/provenance, unchanged mtime, changed-file backup, backup and replace failures, interrupted manifest recovery, invalid manifest, offline restore, corrupt-backup rejection, lock overlap before request, partial source failure, empty range, and IFIX-data isolation.
- `backend/.venv/Scripts/python.exe -m backend.src.internet_data_getter --help`: exited 0; listed `ifix`, `ibovespa`, and both nonconflicting restore subcommands.
- `backend/.venv/Scripts/python.exe -m backend.src.internet_data_getter restore-ibovespa --help`: exited 0 and displayed required year and manifest-relative backup arguments.
- `backend/.venv/Scripts/python.exe -m compileall -q backend/src/internet_data_getter`: exited 0.
- `git diff --check`: exited 0; source-inspection evidence JSON parses with `python -m json.tool`.
- The implemented live `B3IbovespaClient.download_year` validated the actual B3 responses for 2011 and 2026 with the expected byte lengths and hashes in `evidence/source-inspection.json`. No complete IBOVESPA CLI acquisition was run, and no annual data files were added. Independent QA must verify the integrated documented invocation and every annual request in the range.

Implementation snapshot: `evidence/implementation-round-1-snapshot.json`, HEAD `a655c6a97e502666d859ba19c310b5f83d1fa238`, code revision `a655c6a97e502666d859ba19c310b5f83d1fa238:sha256:829613d9f305abc09177399fbc0ae74dab4ef1271167214a373338224c56461b`.

The acquired-file, backup/restore and report paths are implemented in `backend/src/internet_data_getter/ibovespa/`; the shared registry includes the getter in default all-getters runs and the explicit `--getter ibovespa` path. IBOVESPA uses independent destination, lock, manifest and backup roots so an IBOVESPA-only run leaves IFIX data untouched.

## Initial implementation round 2 — RF-001 and RF-002 repairs

### Observed regression reds and greens

- **RF-001 update red:** Ran `backend/.venv/Scripts/python.exe -m unittest backend.src.internet_data_getter.tests.test_ibovespa_acquisition.IbovespaStorageTests.test_first_pending_manifest_failure_does_not_orphan_update_backup -v`. After injecting a failure on the first pending-manifest write, the original active bytes remained intact; retry left 2 backup files but only 1 manifest reference (`AssertionError: 2 != 1`).
- **RF-001 restore red:** Ran `backend/.venv/Scripts/python.exe -m unittest backend.src.internet_data_getter.tests.test_ibovespa_acquisition.IbovespaStorageTests.test_first_pending_manifest_failure_does_not_orphan_restore_backup -v`. After the same failure during restore, the active new bytes remained intact; retry left 3 backup files but only 2 manifest references (`AssertionError: 3 != 2`).
- **RF-002 unterminated CSV red:** Ran `backend/.venv/Scripts/python.exe -m unittest backend.src.internet_data_getter.tests.test_ibovespa_acquisition.IbovespaSourceTests.test_validation_rejects_unterminated_quoted_field_at_eof -v`. Validation accepted the fixture and failed with `AssertionError: DownloadError not raised`.
- **RF-002 blank summary label red:** Ran `backend/.venv/Scripts/python.exe -m unittest backend.src.internet_data_getter.tests.test_ibovespa_acquisition.IbovespaSourceTests.test_validation_rejects_blank_summary_label -v`. Validation accepted the fixture and failed with `AssertionError: DownloadError not raised`.
- **Green:** Reran those four regression cases plus `test_validation_allows_duplicate_nonempty_summary_labels_seen_from_b3`: 5 tests passed. The duplicate-label case ensures validation remains structural and does not impose a distinct-label rule that the live B3 export does not meet.

### Round 2 integrated checks

- `backend/.venv/Scripts/python.exe -m unittest discover -s backend/src/internet_data_getter/tests -v`: **56 tests passed**, including the full existing IFIX suite and the IBOVESPA suite.
- `backend/.venv/Scripts/python.exe -m compileall -q backend/src/internet_data_getter`: exited 0.
- `git diff --check`: exited 0.
- Direct live `B3IbovespaClient.download_year` check: 2011 returned 3,052 bytes with SHA-256 `c232d0921337496042d9241f7ac0a78db625b6c9de0eb0ca31e69aa4da41df9f`; 2026 returned 2,875 bytes with SHA-256 `74f1046d61fc6011cbf0ff62873a9475435778a1247ecc3e8b1e0aeedb9450b9`. Both passed strict CSV validation. No files were stored during the live check.
- RF-001 fix: if the first write-ahead manifest update fails, the store checks that the active file still matches its old hash and that the on-disk manifest does not reference the just-created backup. It then removes only that unreferenced copy; if the manifest cannot prove the backup is unreferenced, it preserves it. The same shared path covers both updates and restores.
- RF-002 fix: the IBOVESPA parser uses strict CSV quote handling and rejects blank summary labels. It still accepts two nonempty summary labels with the same text, as observed in B3's CSV.
- RF-003 remains the round-1 process-evidence limitation described above; no missing historical red runs were reconstructed.

Implementation round 2 snapshot: `evidence/implementation-round-2-snapshot.json`, HEAD `a655c6a97e502666d859ba19c310b5f83d1fa238`, code revision `a655c6a97e502666d859ba19c310b5f83d1fa238:sha256:ebb39f82809ad920818ce0a8806b4c0963be28981e1ebb51a0ca2dfb2da0a1fe` (captured after the repairs, documentation and checks).


## Independent QA — initial cycle round 2 — 2026-11-03

Inputs: approved spec s001 and plan p001; code snapshot `a655c6a97e502666d859ba19c310b5f83d1fa238:sha256:ebb39f82809ad920818ce0a8806b4c0963be28981e1ebb51a0ca2dfb2da0a1fe`. Environment: Windows PowerShell, `backend/.venv`; the feature is a command-line data getter, so project-browser QA is not applicable.

The independent full getter command `python -m unittest discover -s backend/src/internet_data_getter/tests -v` passed all 56 tests, including IFIX regressions. I then ran the documented CLI `python -m backend.src.internet_data_getter --getter ibovespa --data-dir <temporary-directory>` against live B3. It exited 0 and saved 16 years, 2011–2026. Every active file matched its manifest SHA-256 and all 16 manifest periods were present. A separate live refetch matched 2011 (3,052 bytes; SHA-256 `c232d0921337496042d9241f7ac0a78db625b6c9de0eb0ca31e69aa4da41df9f`) and 2026 (2,875 bytes; SHA-256 `74f1046d61fc6011cbf0ff62873a9475435778a1247ecc3e8b1e0aeedb9450b9`) byte-for-byte against the temporary saved files.

I reran the CLI against the same temporary destination. It exited 0 with all 16 years reported unchanged; every file modification time remained identical and no backups were created. The live run wrote outside the project, so no project IFIX or IBOVESPA source data was changed. The test suite independently covers malformed/denied responses, partial failures, lock conflicts, cross-asset isolation, backup/restore, manifest recovery and write failures; the round 2 reviewer additionally fault-injected update and restore failures for both assets.

**QA result:** AC-001 through AC-007 pass on this snapshot. `evidence/qa-initial-round-2-results.json` records the expected and actual behavior per criterion. Snapshot files before and after QA are `evidence/qa-initial-round-2-before.json` and `evidence/qa-initial-round-2-after.json`; they are expected to match. RF-003 remains an explicitly documented nonblocking process limitation: storage/service TDD red evidence from initial round 1 was not observed and has not been reconstructed.
