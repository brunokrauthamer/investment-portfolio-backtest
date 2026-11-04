# Daily returns in reais — review

At record creation, no implementation or review had occurred; specification s001 and plan p001 were proposed for approval.

## 2026-11-04 — Independent review, initial round 1

**Verdict: changes required.** Approved s001 (`3e18c0dc6d4ceb5669c00593debfe0d65269fb5795d4f66f174b59af62798efb`) and p001 (`4127dce2086aaf7475f083ed1212a0e0d56fb14734a89acc515f54c7a46acd50`) were reviewed on `4371d83c90b5306b05eef12ee7395e2912dce711:sha256:f2c350b916218b1cf70cf89cae145bbf2cae73572cbd501c097fb0b2f0bac92b`. The [before](evidence/review-initial-1-before.json) and [after](evidence/review-initial-1-after.json) snapshots matched.

| Finding | Severity | Criteria | Location and consequence | Evidence |
| --- | --- | --- | --- | --- |
| REV-001 | P2, blocking | AC-006 | `backend/src/market_data_normalizer/daily_returns/service.py:38` and `:59`. Pandas pads an underwidth row with `None` while preserving the range index and headers. The parser raises a raw `AttributeError` while reading gathered numbers (and similarly when reading an underwidth currency price) instead of rejecting the malformed source through the exported `NormalizationError`. A caller using that input error type cannot handle this failure, and the exception gives no source or row context. | With valid headers, a full 2011-01-03 row, and existing sentinel output, append `2011-01-04,110,20,0.04` to gathered data. The public function raised `AttributeError: 'NoneType' object has no attribute 'strip'`. Sentinel bytes were preserved. The same row ending in a comma or quoted empty field is a valid blank S&P observation and must still yield zero. [Probe output](evidence/review-initial-1-csv-width.txt). |
| REV-002 | P3, nonblocking | AC-007 | `backend/src/market_data_normalizer/README.md:45`. The README says unsorted dates are rejected without qualifying the source. The order requirement applies to gathered dates, while currency records are sorted for lookup and the active file is in descending order. | Compare gathered validation at `daily_returns/service.py:85` with currency lookup at `:128` and the source CSV. Clarify which input must be ascending. |

Reviewed the complete tracked and untracked feature diff, the package boundary, tests, documentation, generated output and lack of dependency or instruction changes. The focused 10 daily-return tests and 12 existing index tests passed with the backend Python 3.9.4 environment. `git diff --check` passed. The developer recorded an observable example failure on a header-only scaffold and passing focused tests after implementation. That evidence demonstrates red for the example and does not establish separate behavioral red observations for every branch.

| Criteria | Evidence |
| --- | --- |
| AC-001 through AC-005 | Independently recomputed every return using Python CSV, Decimal arithmetic and an as-of date lookup. Checked all 4,085 rows and 16,340 return values. The maximum absolute difference was approximately 4.62e-16. The date list equals the gathered dates after the first row. The 2011-01-04 example, 2011-01-17 S&P blank and resumption, 2011-03-07/08 local blanks and 2011-03-09 resumption, and 2026-11-04 currency fallback were included. Regeneration in an isolated copy matched the delivered file byte for byte. [Artifact checks](evidence/review-initial-1-actual-data.txt). |
| AC-006 | Reviewed initial state and input checks. Focused cases cover staggered starts, duplicates, non-finite and nonpositive values, unsorted dates and atomic replacement failure. The tracked sources have no diff and both input hashes match the baseline. Underwidth rejection needs REV-001. |
| AC-007 | Confirmed the callable and package export, optional data root, default root derived from the module path, and import path with no application CSV or network calls. Inspected invocation and architecture docs. Currency ordering needs the README clarification in REV-002. |

The getter suite ran 123 tests twice using the same Python 3.9.4 environment with Beautiful Soup 4.15.0. A temporary Git archive of the getter subtree at baseline HEAD and the integrated worktree produced the same six S&P pagination subtest failures. No getter code or dependency manifest changed. These are confirmed baseline failures outside the normalizer feature and do not block this feature. [Baseline comparison](evidence/review-initial-1-getter-baseline.txt).

Route REV-001 for a regression-first repair and re-review. Include the README clarification in that pass.


## 2026-11-04 — Independent review, initial round 2

**Verdict: passed.** Reviewed approved s001 (`3e18c0dc6d4ceb5669c00593debfe0d65269fb5795d4f66f174b59af62798efb`) and p001 (`4127dce2086aaf7475f083ed1212a0e0d56fb14734a89acc515f54c7a46acd50`) on `4371d83c90b5306b05eef12ee7395e2912dce711:sha256:47883fbe00c2ccf93be3192f2af4cf7e44b4204fdd9135ba9127b3c245aacfc2`. The [before](evidence/review-initial-2-before.json) and [after](evidence/review-initial-2-after.json) snapshots matched.

- **REV-001 resolved (AC-006).** The developer recorded both underwidth-row regressions failing before the repair. Both now pass in the 12-test daily-return suite. An independent public-call probe confirmed the contextual `NormalizationError` and preservation of an existing output for each input type, and a zero return for a fully formed row with an explicit blank S&P field. [Developer red](evidence/tdd-red-underwidth-round-2.txt), [focused run](evidence/review-initial-2-focused.txt), [independent probes](evidence/review-initial-2-csv-width.txt).
- **REV-002 resolved (AC-007).** The README now distinguishes the strictly ascending gathered dates from the currency source, whose dates may appear in any order. The focused suite includes reversed ordering across currency files.

The only changed paths between the reviewed snapshots are the service, focused tests, and README. Service changes reject absent CSV fields before parsing and preserve handling for explicit blank cells. The calculation, currency matching, default root, import and output publication paths are unchanged. Both real input files and the output artifact retained their round 1 hashes, so the earlier independent comparison of all 16,340 values and byte-for-byte regeneration still apply to AC-001 through AC-005. The 12 existing index normalizer tests and `git diff --check` passed. Neither getter code nor the dependency manifest changed, so the baseline classification of the six getter pagination failures still applies.

No open review findings. Proceed to independent QA.
