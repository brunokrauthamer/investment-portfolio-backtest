# Review

No implementation review has been performed.

## 2026-11-03 — initial cycle, round 1 — changes requested

Reviewed approved s001 (`7d7e85bfbf90acd32ce5f39bbf4818a9ec9ea4b11f24082697283c0622429247`) and p001 (`74021c3e5bd4863ec3b67def549d1798858e000a28601073c2f4049e53a1e7ca`) against snapshot `f0e6c7622a274e0ed439dfd6d523e7591abb0b08:sha256:0f9eadf197593ee395456c29b7d092baad713f1445636c034735ae0a6b4572e0`. Before/after snapshots match: [before](evidence/review-initial-1-before.json), [after](evidence/review-initial-1-after.json). A bytecode file created by a review reproduction was removed before the final snapshot; no implementation or tests were modified.

### Independently executed checks

- `python -m unittest discover -s backend/tests -v`: all 16 tests passed (Windows/Python 3.9).
- Controlled-response and temporary-directory reproductions exercised malformed CSV acceptance, manifest-write interruption and rerun, nested malformed manifest, and the documented restore flow. All four defects below were observed directly. Dummy markers were non-market bytes; no historical observations were fabricated or persisted.
- Inspected the complete integrated changes, including the untracked Python source and test module, all four changed durable README files, approved task records and project context. No source network check was run by this reviewer; independent live QA is still required by AC-007.

### Findings

**RF-001 — P1, blocking — reject malformed/truncated annual CSVs before replacing valid source data.**

Location: `backend/src/acquisition/ifix.py:81-95`. Criteria: AC-002, AC-003, AC-004, AC-006. `_validate_csv` accepts any payload with the two expected headers and one day-labelled row containing any nonblank text, regardless of row width or missing remainder. Direct reproduction through `B3IfixClient.download_year(2011)` returned `b'IFIX - 2011\r\nDia;Jan;Fev;Mar;Abr;Mai;Jun;Jul;Ago;Set;Out;Nov;Dez\r\n1;INVALID_TRUNCATED_ROW\r\n'` as a successful download. This malformed two-column data row is not a valid twelve-month B3 matrix, yet it can replace a valid historical file and produce a complete report. Validate the observed source structure sufficiently to reject malformed/truncated downloads while accepting a structurally complete current-year file with blank future cells. Add a specific failing regression before fixing it.

**RF-002 — P2, blocking — recover provenance and backup references after manifest-write failure/interruption.**

Location: `backend/src/acquisition/ifix.py:232-257`. Criteria: AC-002, AC-004, AC-006; plan crash-recovery requirement. Active replacement occurs before metadata commit, with no recovery record. Reproduction: save old bytes; patch `_atomic_write` to raise `OSError('manifest replace failed')` only for `manifest.json`; save changed bytes; rerun the same changed download without the patch. The first save raises after replacing active bytes; the rerun reports `unchanged`; a backup exists on disk but the final manifest's `previous_versions` is empty. Thus a successful rerun permanently omits the backup created by the failed update, and the documented backup listing cannot be relied upon. Add interruption/recovery regressions and make provenance/backup metadata recoverable across this failure boundary.

**RF-003 — P2, blocking — validate nested manifest records before changing active files.**

Location: `backend/src/acquisition/ifix.py:191-202,232-237`. Criteria: AC-002, AC-003, AC-004, AC-006. The outer shape check permits `files['2011'] = null` (and other invalid nested types). Saving a changed 2011 file then replaces active bytes before raising `AttributeError: 'NoneType' object has no attribute 'get'`. Observed output confirmed `active changed despite invalid manifest: True`. An invalid provenance record must be detected before mutation and reported as an actionable manifest error; a failed save must not silently change data under invalid metadata. Add a failing regression for nested record and version-list validation before repairing it.

**RF-004 — P2, blocking — provide a restore procedure that retains the restored version safely.**

Location: `backend/src/acquisition/README.md:17`; tests around backup/restore. Criteria: AC-004, AC-006; project data-safety rule. The instructions say to copy the backup over the active file and rerun acquisition to refresh the manifest. Reproduction with old/new dummy source bytes: update to new, copy the old backup into active, rerun against the new source. The rerun succeeds and immediately replaces the restored old file with the new source (`active still restored: False`). The copy step also lacks the required recoverable backup and atomic write. Document and verify a safe offline restore path that backs up the displaced active file, atomically installs the selected backup and updates provenance without redownloading over it. A restore command is optional; do not expand scope unnecessarily.

**RF-005 — P2, nonblocking process limitation requiring explicit lead disposition and relevant human acceptance.**

Location: `verification.md`, developer initial-round-1 evidence. Related plan: p001 steps 2–3 and feature-tdd workflow. The developer candidly records that only the source-year behavior and two later regressions have observed behavioral red/green evidence. Other behaviors were authored in tests before implementation but not observed failing; the initial import failure is not behavioral red evidence. Do not reconstruct unobserved test history or describe this as full TDD compliance. Preserve this limitation and obtain an explicit disposition; all repair defects must now use observed regression red/green evidence.

### Architecture and scope observations

Source, orchestration and storage are separate classes/functions with independently testable dependencies, and imports have no executable network calls. All reside in `acquisition/ifix.py`, whereas p001 placed orchestration under `application/` and storage under `storage/`. The lead should record a justified organization decision or have the developer align the file locations; this observation does not change acceptance criteria. There is no frontend/API/scheduler or synthetic dataset. Durable project context still describes acquisition as unimplemented; affected documentation should remain consistent when the repair pass updates it.

Verdict: changes requested. RF-001 through RF-004 block approval of the current implementation. Independent QA has not run.

## 2026-11-03 — initial cycle, round 2 — pass with recorded process limitation

Independently reviewed approved s001 (`7d7e85bfbf90acd32ce5f39bbf4818a9ec9ea4b11f24082697283c0622429247`) and p001 (`74021c3e5bd4863ec3b67def549d1798858e000a28601073c2f4049e53a1e7ca`) against snapshot `f0e6c7622a274e0ed439dfd6d523e7591abb0b08:sha256:a130928277e0cc11c444d8e0cbc15d2b3a8a0c0be35d6cda56bde9ad35f10420`. The [before](evidence/review-initial-2-before.json) and [after](evidence/review-initial-2-after.json) snapshots match. No application, test, configuration or durable-documentation files were changed during this review.

### Independent assessment and executed checks

- Inspected all integrated code and tests, including untracked files, the seven changed durable documentation files, approved specification/plan and review/evidence history. Source protocol, application orchestration and storage now follow the approved module boundaries. Scope remains an explicit command with original-file preservation, without a dashboard, API or scheduler.
- `python -m unittest discover -s backend/tests -v`, with bytecode writes disabled through the environment, passed all 22 tests. [Test output](evidence/review-initial-2-tests.txt).
- Independently exercised the earlier malformed CSV, interrupted final manifest commit, nested malformed manifest and offline restore cases in temporary directories. Also simulated active-file replacement failure followed by a successful retry. [Reproduction outcomes](evidence/review-initial-2-reproductions.txt). Dummy markers were non-market bytes and no source dataset was fabricated or saved in the repository.
- Inspected the explicit import/entry-point boundaries, default verified HTTPS requests, error-to-incomplete reporting, runtime year range, stable filenames, source byte preservation and manifest fields, locking, verified backups and atomic writes. No import-time network call exists. This review did not independently contact B3; AC-007 still requires independent source-backed QA.

### Prior finding dispositions

- **RF-001 — resolved.** The exact earlier two-column truncated payload is now rejected. Validation requires the observed 35 nonempty rows, 31 ordered day rows and 13 columns per day, with two summary rows and at least one populated cell. A complete matrix with blank future months passes. This checks source structure without rewriting the downloaded bytes.
- **RF-002 — resolved.** An injected failure of the final manifest commit leaves a write-ahead entry. On rerun it is reconciled against the active hash, and the old-byte backup remains recorded and hash-verifiable; pending metadata is cleared only after recovery. The same protocol covers restore. An independently injected active replacement failure preserved old data and a subsequent retry recovered successfully.
- **RF-003 — resolved.** Independently tested a null file record, a non-list `previous_versions`, and a null history entry. Each is rejected with `ManifestError` before active mutation. The normal nested schema and backup-path validation occur before save mutation.
- **RF-004 — resolved.** The documented offline restore CLI verifies a manifest-listed backup and its CSV structure, preserves the displaced active bytes in another verified backup, installs selected bytes atomically, updates restore provenance, and makes no B3 download call. The documented procedure retains the restored bytes; it explicitly explains that a later separate acquisition can update them again.
- **RF-005 — remains open, nonblocking process limitation.** The incomplete initial-round observed red/green history cannot be reconstructed. Round-2 evidence records the four specific pre-fix regression failures and their passing repairs, but does not erase the earlier limitation. The lead must record a disposition and obtain relevant human acceptance rather than claim full original TDD compliance.

Verdict: **pass for the implementation/architecture review on this snapshot**, with RF-005 explicitly retained for lead disposition/human acceptance. No unresolved blocking review finding remains. Proceed to independent integrated QA immediately; this review is not a QA verdict or delivery approval.

## 2026-11-03 — review-only refresh after actual project acquisition — pass

Evaluated current approved s001/p001 against data-inclusive snapshot `f0e6c7622a274e0ed439dfd6d523e7591abb0b08:sha256:fe8395f944e4b0e1d7c652138b00d1fb5045ebeb18c60f0d922eba67603c2c4c`. [Before](evidence/review-acquired-data-before.json) and [after](evidence/review-acquired-data-after.json) snapshots match. This is a review-only refresh; no implementation round was dispatched and no data or code was changed by the reviewer.

### Impact and independent checks

- Compared every path/hash/mode in the last independently reviewed snapshot with the current snapshot: exactly 17 additions under `data/ifix/` (16 annual CSVs and `manifest.json`), no removed files, no modified files, and the same Git HEAD. Thus the prior independent code/architecture/documentation assessment, all 22 passing tests and RF-001 through RF-004 regression outcomes remain applicable to identical inputs; these tests use controlled temporary destinations and do not depend on repository source data. Repeating them would not assess an additional changed behavior.
- Independently checked all 16 stored CSVs, 2011 through 2026, against the manifest: stable year/name, original source filename, source URL, retrieval timestamp, SHA-256, year and month headers, 31 day rows, 13 columns per row, two summary rows and valid calendar dates for populated cells. All checks passed. The source folder contains exactly these 16 files, with no leftover lock, temporary file or pending transaction. Initial-download history lists no prior versions, as expected.
- Recorded complete metadata and snapshot differences in [data/provenance checks](evidence/review-acquired-data-checks.json). The 2011 file has 2,741 bytes and SHA-256 `8b338666afc34865d00af732898ea2cd58cdc1bc8b1fe535983fffe2bf4a8d20`; 2026 has 2,419 bytes and SHA-256 `48aed9dcc56b44d6b651a4bb20b937606919121ecddffbebb08835b6dcc1050f`, matching the earlier source inspection hashes. The latest observed date in the saved current-year matrix is 2026-10-30. This checks stored source coverage, not trading-calendar completeness.
- Both original export summary labels are `MÍNIMO`; these bytes are preserved without correction or interpretation. An initial independent check assumed min/max labels, then was corrected to inspect the actual source structure. That check assumption was not an implementation defect.

Verdict: **pass on the current data-inclusive snapshot**. No new blocking finding. Prior resolved findings remain resolved; RF-005 remains the nonblocking original TDD-history limitation requiring lead disposition and relevant human acceptance. Independent QA must refresh its current-snapshot verdict for the added acquired data; this review does not update QA fields or constitute delivery approval.
