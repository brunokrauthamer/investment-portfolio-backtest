# Review

## 2026-11-03 — initial cycle, review round 1

**Verdict: changes required.** Reviewed approved s001 (`7c8cb5d3b7ab546e954d2e53396c37e4161730b1012dc02819746df2f17bd794`) and p001 (`6b7c698bfac8d8099812fa19ed8c6fba54a3cb0d15655fe8b33261f15c9c001f`), AC-001–AC-007, on snapshot `f218c35e050e196a47e724ee348def9035671601:sha256:244a06b5942c43b9b2c961ed2cfd4dc6021b9da3d091b6154bb23c82435c5703`. Before/after snapshots match. No implementation edits or project data acquisition occurred in review.

Inspected the complete tracked and untracked implementation, registry, tests, and documentation. `backend/.venv` unittest discovery passed all 40 tests and `git diff --check` passed. Reproductions are in [live trace](evidence/review_live_sgs.py), [offline probes](evidence/review_offline_reproductions.py), and the [before](evidence/review-initial-1-before.json)/[after](evidence/review-initial-1-after.json) snapshot records. The live trace is a focused diagnosis, not a complete acquisition or QA pass.

| ID | Severity | Criteria | Location and finding |
| --- | --- | --- | --- |
| RF-001 | P1, blocking | AC-002, AC-003, AC-007 | `selic/source.py:167–190` — the top-level DOM may load before the static-chart iframe's form, so the refresh click fails to issue its POST and an old image can satisfy the current wait. The read-only trace reproduced a correct values POST but a stale 03/11/2016–03/11/2026 result (2,508 records) with no refresh POST. Waiting for the iframe form and `atualizarGraficoEstatico` POST response returned 01/01/2011–30/10/2026 (3,976 records). This is an implementation race; the source served the requested range with correct synchronization. |
| RF-002 | P1, blocking | AC-004, AC-005 | `selic/storage.py:182–212` — recovery decides from the active CSV hash alone and can destroy unrecognized provenance. After interrupting the new manifest write, the probe placed unrelated bytes at the manifest path; recovery overwrote them and removed the pending record. Validate both pending/current CSV and manifest states (including an idempotent rollback state), and stop without overwriting either when state is ambiguous. |
| RF-003 | P2, blocking | AC-004, AC-005 | `selic/storage.py:232–241,288–327` — each saved backup embeds the prior `current` including its complete backup history, creating exponential manifest growth and eventually making routine revised acquisitions and recovery impractical. Ten distinct fixture saves grew the manifest from 836 to 715,714 bytes. Preserve flat references to verified paired backups; the prior manifest already holds historical provenance. |
| RF-004 | P2, blocking | AC-004, AC-005 | `selic/storage.py:302–327` — offline restore routes through the new-acquisition path and replaces original retrieval metadata. The probe restored a version retrieved February 1, 2026, and its active record claimed it was retrieved February 11, when no source request occurred. Retain verified historical source provenance and separately identify the local restore time. |
| RF-005 | P2, blocking | AC-002, AC-003 | `selic/source.py:115–132,168–174` — source identity checks search for `11` anywhere in the table, and the result header is not checked for the series code. An offline page with series `111 - Interest rate - Selic` and an end date `11/02/2011` passed `_verify_values_page`. Verify the exact code in the appropriate source metadata and data-column header instead of matching a date token. |
| RF-006 | P2, blocking | AC-003 | `selic/source.py:194–214` — reaching the reported row count ends the run before checking that pagination actually ended; contradictory `Next` navigation can be ignored even if further source pages contain rows or a malformed repeated page. Require the source-indicated end and count together; test count reached on a nonfinal page and the repeated/missing-page paths. |
| RF-007 | P3, blocking | AC-006 | `tests/test_selic_acquisition.py:33–52,73–76,268–271` — fixtures reproduce actual January 2011 BCB date/value pairs observed in browser discovery, although the criterion calls for controlled non-market test observations. Substitute clearly controlled values and keep live comparisons separate. |
| RF-008 | Process limitation | AC-006 | `verification.md`, initial round 1 TDD evidence — some tests were written after implementation, so their intended pre-implementation reds were not observed. Keep this recorded, do not reconstruct history, and record actual pre-fix reds for every confirmed repair. |

Follow-up: route RF-001–RF-007 to the next bounded repair pass. Preserve RF-008 and obtain lead disposition. Independent re-review and live QA remain outstanding.


## 2026-11-03 — initial cycle, review round 2

**Verdict: changes required.** Reviewed approved s001 (`7c8cb5d3b7ab546e954d2e53396c37e4161730b1012dc02819746df2f17bd794`) and p001 (`6b7c698bfac8d8099812fa19ed8c6fba54a3cb0d15655fe8b33261f15c9c001f`) on snapshot `f218c35e050e196a47e724ee348def9035671601:sha256:10bd2d156a6c160251c2b8a31292be39a5bdd12c25e68e4379389624f3a0a474`. The [before](evidence/review-initial-2-before.json) and [after](evidence/review-initial-2-after.json) snapshots match. Reviewed all tracked and untracked product files. The full getter suite passed 45 tests, and `git diff --check` passed with line-ending normalization warnings. The reviewer ran the temporary live smoke independently. It returned 3,976 observations, from 2011-01-03 through 2026-10-30, with CSV SHA-256 `21e0e6a98aebd0b27f8c9d7f7b07f37d0bffe9d0d96ff85ebda20319d23c6a6f`. The default sandbox denied outbound browser access, and the approved network-enabled run passed. Project data was not written.

| ID | Disposition | Independent evidence |
| --- | --- | --- |
| RF-001 | Resolved | The integrated live smoke completed at the full requested range after the iframe/refresh synchronization. |
| RF-002 | Resolved | An unknown active manifest and the pending record both retain their exact bytes after a simulated interruption. The test suite also exercises interruption during rollback. |
| RF-003 | Resolved | Ten fixture versions grew the active manifest from 836 to 5,115 bytes. Its references do not embed prior records. |
| RF-004 | Resolved | A verified offline restore retained the original February 1 retrieval time and recorded a distinct February 11 local restore time. |
| RF-005 | Resolved | The exact-series checks reject code 111 in selected-series metadata and the values header. The browser run accepted the real SGS 11 structure. |
| RF-006 | Resolved | The suite exercises repeated pages, premature end, and navigation remaining after the count is reached. The complete live run reached the page and count end. |
| RF-007 | Resolved | Inspected the corrected controlled fixture values and reran the offline suite. |
| RF-008 | Open, nonblocking | The historical TDD evidence limitation remains recorded. Round 2 documents observed reds for the behavioral repairs. |

| ID | Severity | Criteria | Location and finding |
| --- | --- | --- | --- |
| RF-009 | P2, blocking | AC-004, AC-005 | `selic/storage.py:124–145,345–358` — validation checks the CSV hash and reference shape but accepts missing or contradictory source provenance. After removing the unit, clearing the retrieval time, and setting the count to 99 for a one-row CSV, a byte-identical acquisition returned `unchanged`, retaining an invalid manifest and reporting completion. Validate the required provenance fields and their agreement with the matching CSV before returning success or using the manifest as a recovery/restore input. Preserve invalid active files for investigation. |
| RF-010 | P2, blocking | AC-003, AC-006 | `selic/source.py:68–78` — every nonmatching date string is treated as a header or footer, so a malformed observation row can be skipped silently. A source-shaped table with two valid endpoints and a numeric-rate row dated `03-02-2011` was accepted as two observations when the reported count was two. Distinguish structural non-observation rows from malformed data rows and fail closed even when the remaining rows match the count. |

The [offline probes](evidence/review-initial-2-probes.py) reproduce RF-002 through RF-004 and RF-009 through RF-010. Route RF-009 and RF-010 to the next bounded repair pass, with observed failing regression tests before implementation fixes.


## 2026-11-03 — initial cycle, review round 3

**Verdict: pass.** Reviewed approved s001 (`7c8cb5d3b7ab546e954d2e53396c37e4161730b1012dc02819746df2f17bd794`) and p001 (`6b7c698bfac8d8099812fa19ed8c6fba54a3cb0d15655fe8b33261f15c9c001f`) on snapshot `f218c35e050e196a47e724ee348def9035671601:sha256:fc8f20234e69450785184f5d7af3a56769108c320d56aa7fd7cb875ade042192`. The [before](evidence/review-initial-3-before.json) and [after](evidence/review-initial-3-after.json) snapshots match. Inspected the updated source, storage, and tests alongside the integrated registry, CLI, and documentation reviewed in round 2. All 48 getter tests passed. CLI help, compileall, and `git diff --check` passed. Git emitted line-ending normalization warnings only.

| ID | Disposition | Independent evidence |
| --- | --- | --- |
| RF-009 | Resolved | Re-running the original offline probe now rejects corrupt provenance on an unchanged acquisition. The regression suite also rejects internally matching manifest counts that disagree with the actual CSV and verifies that invalid active files remain unchanged. The normal rerun, interrupted commit, and offline restore tests pass with paired CSV/provenance validation. |
| RF-010 | Resolved | Re-running the original malformed-date probe now rejects the table. The browser scrape with the tightened parser accepted the actual table and its pagination. |
| RF-001–RF-007 | Resolved | The previously reviewed fixes remain integrated. The 48-test suite, the rerun [offline probes](evidence/review-initial-2-probes.py), and the current live temporary scrape retain evidence for the affected behavior. |
| RF-008 | Open, nonblocking | Some first-round pre-implementation reds were not observed. The limitation remains recorded, and the round 2 and 3 regressions have observed red and green evidence. |

The reviewer independently reran the [temporary live smoke](evidence/implementation-round-2-live-smoke.py) on this snapshot. The run completed with 3,977 observations from 2011-01-03 through the current BCB-reported date of 2026-11-03. CSV SHA-256 was `b9f3d96ac8504f77bcc08fdbe3024eb2e760c9e8190a8fba726a20ad79414688`. This is a reviewer smoke check. Independent QA and project-data acquisition remain outstanding.


## 2026-11-03 — project-data review refresh

**Verdict: pass.** Reviewed the effects of the planned project acquisition on AC-004, AC-005 and AC-007, under approved s001/p001, on snapshot `f218c35e050e196a47e724ee348def9035671601:sha256:0979d83d473acf782bdebe9332592698aa65e0b2509d1a0e66ba00b8a5adbdf1`. The [before](evidence/review-project-data-before.json) and [after](evidence/review-project-data-after.json) snapshot files match byte for byte. Compared the full path hashes with the prior reviewed snapshot and verified that the only differences were the new CSV and manifest. Code, tests, configuration, and documentation have the same hashes, so the prior integrated review and 48-test evidence remain applicable to their unchanged behavior.

Independently decoded the project CSV as UTF-8 and checked its exact header, two-column rows, decimal text, and 3,977 unique dates in increasing ISO order from 2011-01-03 through 2026-11-03. Checked the manifest’s source and dataset URLs, series, unit, license, retrieval time, date range, counts and CSV format against the approved conventions. The computed CSV SHA-256 matches both the manifest and the reviewer’s prior temporary live BCB scrape, `b9f3d96ac8504f77bcc08fdbe3024eb2e760c9e8190a8fba726a20ad79414688`. The project CSV’s first, middle and last sampled rates match the independent browser evidence in [QA’s live run](evidence/qa-initial-3-live-cli.txt). The first save has an empty backup history and left no Selic backup, lock or pending transaction. Details are in the [independent validation results](evidence/review-project-data-validation.json).

No new findings. RF-008 remains an open nonblocking limitation on the first-round process evidence. Independent project-data QA remains separate from this review verdict.
