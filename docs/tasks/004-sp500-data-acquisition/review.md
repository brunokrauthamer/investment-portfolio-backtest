# Review

No integrated implementation has been submitted for review. Specification s001 and plan p001 are proposals pending explicit approval.

## Initial cycle, round 1 — 2026-11-04 (America/Sao_Paulo)

**Verdict: changes required.** Approved specification `s001` and plan `p001` were checked against `134437fadf082e61161d60f8ad06dc2456a1d0d0:sha256:067a8f4b05b21f6f765a50ddf3b406e6d812f92b58e33b2b327dba18098e76a2`. The [before](evidence/review-initial-1-before.json) and [after](evidence/review-initial-1-after.json) snapshots match.

- Inspected tracked integration/docs/test edits, untracked getter modules and tests, and the new data pair. Existing getter assertions were extended for the new registration; no earlier behavioral assertions were removed. The getter separates the source, orchestration, CLI, and file-store responsibilities without modifying the older asset implementations.
- Executed `backend/.venv/Scripts/python.exe -m unittest discover -s backend/src/internet_data_getter/tests` independently: 105 tests passed on Windows, Python 3.12.14. `git diff --check` passed with a line-ending warning only for the excluded interaction log. No live request was made and no active data was modified.
- Independently validated the existing CSV/manifest pair: 3,983 observations, Jan 3, 2011 through Nov 3, 2026; CSV SHA-256 `16a20e865a738b45fd7bdfc7214a650a1d79921d44b01b7d6d71c67d04587a55`. This verifies local integrity, not completeness of the original source.
- Developer evidence correctly distinguishes import/setup errors and records behavioral reds for specific cases; it does not establish pre-implementation behavioral reds for every source/storage behavior. Treat this as an evidence limitation; do not reconstruct red results. For the confirmed defects below, require a failing regression before each fix and a later passing result. Existing tests cover normal dates, adjusted-close extraction, incremental windows, unchanged CSV, locking, one interrupted write, and restore. They missed the independent offline adversarial probes below.
- Criteria reviewed: AC-001 registry/import and CLI tests pass, with a documentation discrepancy; AC-002 UTC bounds are correct for generated URLs, but redirects undermine the actual interval; AC-003–004 have the source-validation findings below; AC-005 local CSV and precision fixtures pass; AC-006 incremental suffix/prefix/overlap and preservation tests pass; AC-007 preserves unchanged CSV but overlaps the AC-009 manifest defect; AC-008–010 normal persistence/restore paths pass, with provenance and recovery blockers; AC-011 commands and dependency are present, with usage-doc discrepancy; AC-012 full offline suite passed but missed these defects and QA is pending; AC-013 permission statement and source restrictions are documented.

### SP500-R1-01 — high, blocking (AC-007, AC-009)

Location: `backend/src/internet_data_getter/sp500/storage.py:448`.

An unchanged acquisition overwrites the provenance manifest with new last-checked fields, without the verified backup and write-ahead transaction required before replacing a changed manifest. The requirement that an unchanged run creates no backup is satisfied by leaving the pair unchanged.

**Evidence:** Save a fixture at 2026-11-04 UTC, then save identical observations at 2026-11-05 UTC. Status is unchanged, but the manifest bytes change with zero backups and no journal.

### SP500-R1-02 — high, blocking (AC-002, AC-004, AC-008, AC-009)

Location: `backend/src/internet_data_getter/sp500/source.py:259`.

The final response URL can identify a narrower Yahoo interval while the result keeps the caller's bounds. A partial subset of the desired history can then be committed under misleading provenance.

**Evidence:** For a request for Jan 3–4, make the mocked Yahoo response's final URL encode Jan 4 only, with one Jan 4 row. `Sp500Acquisition.run` reports `saved`, one observation, and no error.

### SP500-R1-03 — high, blocking (AC-004, AC-008)

Location: `backend/src/internet_data_getter/sp500/source.py:143`.

Explicit pagination can be silently accepted. Detection recognizes only Show/Load More text or aria-label and is skipped entirely when a table is absent and a no-data message matches.

**Evidence:** Append `<a rel="next" href="?page=2">Next</a>` to a valid history fixture. The parser accepts both rows. An otherwise valid no-data page with `<button>Show More</button>` is also accepted as an empty result.

### SP500-R1-04 — high, blocking (AC-003, AC-008)

Location: `backend/src/internet_data_getter/sp500/source.py:169`.

Substring matching accepts a different symbol as `^GSPC`; those observations can be recorded as the requested S&P 500 data.

**Evidence:** Replace `^GSPC` in both the title and heading of the normal fixture with `^GSPCX`. The parser returns two observations without an error.

### SP500-R1-05 — high, blocking (AC-004, AC-008)

Location: `backend/src/internet_data_getter/sp500/source.py:186`.

A date-like incomplete row containing the word Dividend is silently discarded before structural validation, even without a recognizable corporate-action row. Date-like rows using header cells are also ignored when no td is present.

**Evidence:** Add `<tr><td>2011-01-03</td><td>Dividend</td></tr>` inside the normal table body. The malformed row is silently discarded and the remaining two observations are accepted.

### SP500-R1-06 — high, blocking (AC-008, AC-009)

Location: `backend/src/internet_data_getter/sp500/storage.py:170`.

The active pair is treated as valid even when required request provenance is missing or contradicts itself. Hash validation protects CSV bytes only, and currently cannot detect a false date-window URL, a missing window list, or a non-timestamp value.

**Evidence:** After saving a valid fixture, change only one manifest field at a time: set `requested_windows` to `[]`; set `retrieved_at` to `2026-11-04Z`; change a window's URL to use another day's Unix bounds; or set `requested_start`/`requested_end` to disagree with the windows. Each invalid variant was accepted by `load()`.

### SP500-R1-07 — high, blocking (AC-008, AC-009, AC-010)

Location: `backend/src/internet_data_getter/sp500/storage.py:375`.

Recovery can complete and delete an invalid write-ahead record for an update even though its required prior version is no longer recoverable. The backup is checked only if the optional-looking `backup` member exists, regardless of the non-null old pair hashes.

**Evidence:** On a temporary store, simulate a manifest write interruption after the CSV is replaced. Remove the `backup` member of the pending record and remove the paired backup files. `load()` commits the new manifest, returns two rows, and deletes the pending record. It should stop and preserve the ambiguous state.

### SP500-R1-08 — low, nonblocking (AC-001, AC-011)

Location: `backend/src/internet_data_getter/README.md:3`.

Shared usage still names only IFIX, IBOVESPA and Selic as registered getters, omits the dedicated Python getter and its dates, and backend/README.md says `sp500` runs only when selected even though the all-getters command includes it.

**Evidence:** Compare the opening shared instructions and backend README with `available_getters()`, `acquire_sp500` and shared `main()`.

Next: route confirmed defects to the developer for targeted regression evidence and an independent re-review before QA.

## Initial cycle, round 2 — 2026-11-04 (America/Sao_Paulo)

**Verdict: changes required.** Re-reviewed approved specification `s001` and plan `p001` at snapshot `134437fadf082e61161d60f8ad06dc2456a1d0d0:sha256:58c626d3743bed813024e026fb0bb1b6e63cb24ef89a7792ddcd7c404ed489a3`. The [before](evidence/review-initial-2-before.json) and [after](evidence/review-initial-2-after.json) snapshots match.

- Inspected the source URL, parser, storage and recovery changes, regression tests, shared registry and CLI, affected documents, and untracked getter and data files. The developer recorded behavioral red evidence before fixing the confirmed round 1 defects. The documentation finding was verified by comparing the revised commands and Python entry point with the registry.
- Executed the full getter suite independently in `backend/.venv` on Windows. All 115 tests passed. `git diff --check` reported no whitespace errors and only the existing interaction-log line-ending warning.
- Independent offline probes in temporary stores rejected 21 round 1 failure variants. These included changed URL dates, anchor and button pagination including empty results, wrong ticker prefixes and suffixes, malformed table rows, inconsistent manifest timestamps and ranges, and incomplete or damaged journal backup pairs. The damaged recovery cases preserved both active files and the journal. An unchanged rerun preserved both files' bytes and modification times and created neither backup nor journal. A changed update backed up the exact old CSV and manifest. Offline restore preserved the restored version's retrieval metadata and backed up the exact displaced pair.
- The acquired dataset still validates at 3,983 rows spanning 2011-01-03 through 2026-11-03 with CSV SHA-256 `16a20e865a738b45fd7bdfc7214a650a1d79921d44b01b7d6d71c67d04587a55`. No Yahoo request or active data edit occurred during review.
- Round 1 dispositions: SP500-R1-01 through SP500-R1-08 are resolved for the reported reproductions. The expanded cases below still block source accuracy and transaction safety. AC-001, AC-002, AC-005 through AC-007, AC-011 and AC-013 showed no new discrepancies in this review. AC-003, AC-004 and AC-008 through AC-010 remain affected by the findings below. AC-012 has independent review and test evidence, with independent QA pending.

### SP500-R2-01 — high, blocking (AC-003, AC-004, AC-008, AC-009)

Location `backend/src/internet_data_getter/sp500/source.py:102`.

URL validation confirms the endpoint and dates but ignores explicit changes to the requested daily history options. A redirect selecting a coarser interval can pass page validation and label sparse observations as daily data. The shared manifest validation also accepts that changed URL.

**Evidence** — Build the normal Yahoo URL and replace only `interval=1d` with `interval=1mo`. Return the changed URL and otherwise valid in-range history HTML from the mocked opener. `YahooFinanceClient.fetch` returns observations instead of rejecting the changed interval. Retain compatibility for harmless query reordering or unrelated redirect parameters.

### SP500-R2-02 — high, blocking (AC-004, AC-008)

Location `backend/src/internet_data_getter/sp500/source.py:171`.

Pagination detection now handles anchor and button controls but ignores a standard document link explicitly declaring the next page. An otherwise structurally valid partial table can be committed.

**Evidence** — Add `<link rel="next" href="?page=2">` before `</head>` in the valid fixture. The parser still accepts both rows. The original anchor and button pagination probes are now rejected.

### SP500-R2-03 — high, blocking (AC-003, AC-008)

Location `backend/src/internet_data_getter/sp500/source.py:161`.

The parser joins title and heading and accepts a single matching ticker anywhere in the result. An explicit conflicting ticker in one identity field is ignored if the other field mentions `^GSPC`, so the page does not unambiguously identify the requested instrument.

**Evidence** — In the valid fixture, replace only its `<title>` with `<title>Dow Jones (^DJI) Historical Data</title>`, leaving its `^GSPC` heading and table unchanged. The parser accepts the rows. The original ticker prefix/suffix probes are now rejected.

### SP500-R2-04 — high, blocking (AC-008, AC-009, AC-010)

Location `backend/src/internet_data_getter/sp500/storage.py:442`.

Recovery chooses a branch using file digests and a structurally valid manifest, before checking the proposed CSV and manifest as a pair. A self-consistent journal with invalid pair metadata overwrites the active manifest and deletes recovery evidence, then `_read_current` discovers the pair cannot be loaded. Validate the applicable pair before replacing metadata or removing the journal.

**Evidence** — With a temporary store, simulate interruption immediately after replacing the CSV during an update. Increase the pending `new_manifest.current.observation_count` by one and update `new_manifest_sha256` to the digest of those serialized bytes, leaving CSV and backup hashes intact. `load()` raises a count mismatch only after overwriting the manifest and removing the pending journal. The original missing or damaged backup cases now reject with all files preserved.

Route the four confirmed defects to the developer for observed failing regression checks, fixes, and independent re-review before QA.

## Initial cycle, round 3 — 2026-11-04 (America/Sao_Paulo)

**Verdict: changes required.** Re-reviewed approved specification `s001` and plan `p001` at `134437fadf082e61161d60f8ad06dc2456a1d0d0:sha256:1ef41338f1050201f21109c961f8b9e1e37f50c0a23d5fcfa253e2331fb485b0`. The [before](evidence/review-initial-3-before.json) and [after](evidence/review-initial-3-after.json) snapshots match. The spec and plan hashes still match the approved values.

- Reviewed the complete integrated worktree, including untracked files. Snapshot comparison with round 2 identified changes only to the source parser/client, the file store, and the S&P 500 tests. The registry, CLI, dependency manifest, usage and architecture documents, and captured Yahoo pair were unchanged from the preceding review.
- Executed the full getter suite independently in `backend/.venv` on Windows. All 121 tests passed. `git diff --check` reported no whitespace errors and only the existing interaction-log line-ending warning. The developer recorded behavioral red evidence for the round 2 findings and the adjacent rollback metadata defect before fixing them.
- Independent probes repeated 21 round 1 negative variants, verified both files' bytes and modification times on an unchanged run, compared the exact paired backups for updates and restores, and confirmed restored retrieval provenance. The 15 round 2 and adjacent rollback cases rejected changed daily selection values in response and manifest URLs, document pagination on populated and empty pages, conflicting caret tickers, and inconsistent candidate or rollback observation counts. The latter cases preserved both active files and the pending record. A reordered query with an unrelated parameter remained valid.
- The acquired local pair still validates at 3,983 observations from 2011-01-03 through 2026-11-03, with CSV SHA-256 `16a20e865a738b45fd7bdfc7214a650a1d79921d44b01b7d6d71c67d04587a55`. No live Yahoo request or active-data edit occurred during review. Yahoo's source completeness beyond detectable errors remains a documented limitation.
- SP500-R2-01 through SP500-R2-04 are resolved for their reported reproductions. The independent probes below found additional blocking cases. AC-001, AC-006, AC-007, AC-011 and AC-013 showed no further discrepancies in this review. AC-002 through AC-005 and AC-008 through AC-010 are affected by the new findings. AC-012 has test and review evidence, with independent QA pending.

### SP500-R3-01 — high, blocking (AC-003, AC-004, AC-005, AC-008)

Location `backend/src/internet_data_getter/sp500/source.py:239`.

The parser checks whether the Date and Adj Close indexes exist but does not require observation cells to align with the headers. An omitted cell before Adj Close shifts Volume into the adjusted price slot. Volume is a valid-looking numeric string, so the bad row can be persisted as a price.

**Evidence** — In the ordinary seven-column fixture, remove only the Jan 3 Close cell (`<td>1,271.87</td>`). The parser returns Jan 3 adjusted close `4286670000`, the row's volume, instead of rejecting the six-cell row. An observation row with the required columns should match the header structure before a numeric value is interpreted.

### SP500-R3-02 — high, blocking (AC-008, AC-009, AC-010)

Location `backend/src/internet_data_getter/sp500/storage.py:441`.

Recovery verifies the displaced backup's files and digests but does not require the manifest it installs to contain that exact backup reference. It can consume the journal and orphan the previous version from the documented offline restore path even though the prior pair was verified.

**Evidence** — Interrupt an update after replacing the CSV but before replacing the manifest. Remove `new_manifest.current.previous_versions` entries from the pending record and recompute `new_manifest_sha256`, leaving the valid recorded `backup` and its files in place. `load()` commits the new manifest with no backup references, deletes the journal, and a subsequent `restore()` of that exact verified prior CSV fails because the reference is unlisted. The same reference relationship needs to hold for candidate and rollback manifests.

### SP500-R3-03 — medium, blocking (AC-002, AC-003, AC-004, AC-008, AC-009)

Location `backend/src/internet_data_getter/sp500/source.py:109`.

Query parsing drops blank values before checking that every required parameter appears once. A final URL and stored provenance can therefore carry ambiguous date or frequency selection even though the validation promises a unique value.

**Evidence** — Append `&period1=` or `&interval=` to the generated URL and use the result as the mocked response's final URL. `YahooFinanceClient.fetch` accepts both variants. A strict duplicate check must count blank values while still allowing unrelated parameters and reordered valid queries.

### SP500-R3-04 — medium, blocking (AC-003, AC-008)

Location `backend/src/internet_data_getter/sp500/source.py:180`.

The conflict check only parses caret-prefixed tickers. It accepts explicit incompatible quote identity from a normal non-caret instrument symbol while another identity field contains `^GSPC`.

**Evidence** — Replace only the title with `<title>Apple Inc. (AAPL) Historical Data</title>` and retain the valid `^GSPC` heading and table. The parser accepts the rows. The prior `^DJI` conflict now rejects in both title and heading.

Initial review has exhausted its three rounds. Route the available independent QA assessment and the evidence to the correction workflow. These findings require regression cases before fixes and an independent re-review of the corrected snapshot.



