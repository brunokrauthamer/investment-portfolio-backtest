# Independent QA resumption — initial round 3

QA was resumed under assignment qa_resume against approved specification s001, plan p001, and code snapshot `134437fadf082e61161d60f8ad06dc2456a1d0d0:sha256:1ef41338f1050201f21109c961f8b9e1e37f50c0a23d5fcfa253e2331fb485b0`.

## Environment and integrity

- Windows worktree, using `backend/.venv/Scripts/python.exe`.
- The before and after code revisions in `qa-resume-before.json` and `qa-resume-after.json` match the assigned code snapshot. No application or durable-document changes occurred during QA.
- No live Yahoo request was made. The existing data pair was read only. The inspected S&P 500 loader validated 3,983 rows from 2011-01-03 through 2026-11-03, 75,697 CSV bytes, SHA-256 `16a20e865a738b45fd7bdfc7214a650a1d79921d44b01b7d6d71c67d04587a55`.
- This is a backend acquisition CLI feature, so product browser QA is not applicable.

## Executed checks

- `backend/.venv/Scripts/python.exe -m unittest discover -s backend/src/internet_data_getter/tests` — 121 tests passed.
- `backend/.venv/Scripts/python.exe -m unittest discover -s backend/src/internet_data_getter/tests -p test_sp500_acquisition.py` — 44 tests passed.
- `backend/.venv/Scripts/python.exe -m unittest discover -s backend/src/internet_data_getter/tests -p test_getter_public.py` — 11 tests passed.
- `backend/.venv/Scripts/python.exe -m backend.src.internet_data_getter fetch-sp500 --help` — exit 0; start and end date flags are shown.
- `backend/.venv/Scripts/python.exe -c "from backend.src.internet_data_getter import available_getters; print(available_getters())"` — printed `('ifix', 'ibovespa', 'selic', 'sp500')`.
- `backend/.venv/Scripts/python.exe docs/tasks/004-sp500-data-acquisition/evidence/qa-round-3-reproductions.py` — independently reproduced all four open round 3 review findings using synthetic HTML fixtures and temporary directories:
  - A missing Close cell shifted Volume into adjusted_close as `4286670000`.
  - A response URL with a duplicate blank period1 value was accepted.
  - A title identifying Apple Inc. (AAPL) was accepted beside a ^GSPC heading.
  - Recovery consumed the journal without retaining the prior backup reference, after which restore rejected that backup as unlisted.
- `backend/.venv/Scripts/python.exe docs/tasks/004-sp500-data-acquisition/evidence/qa-round-3-active-pair.py` — validated the active data/manifest pair and reported the coverage, byte size, row count, and digest above.
- `git diff --check` — no whitespace errors; Git reported only the existing LOG.md LF-to-CRLF conversion warning.

## Acceptance matrix

| Criterion | Result | Expected and observed behavior |
|---|---|---|
| AC-001 | Pass | `sp500` is in the shared registry; focused and shared-entrypoint suites pass; the public CLI help is available. The tests cover imports without a network request. |
| AC-002 | Fail | UTC timestamp bounds and date flags pass their checks, but the client accepts an ambiguous final URL with duplicate blank period1. |
| AC-003 | Fail | The parser accepts conflicting instrument identity: an AAPL title beside a ^GSPC heading. |
| AC-004 | Fail | A malformed row with one omitted cell is accepted instead of rejected, so a partial row can be misread as a valid observation. |
| AC-005 | Fail | The malformed-row reproduction produced adjusted_close `4286670000`, the Volume value, instead of rejecting the row. |
| AC-006 | Pass | The focused suite passes its later extension, latest-date overlap, earlier backfill, two-window extension, and narrower-range preservation checks. |
| AC-007 | Pass | The focused suite passes the unchanged-data check, which preserves CSV and manifest bytes and creates no backup. |
| AC-008 | Fail | Malformed source rows can be committed, and recovery can consume its journal while losing the prior restore reference. |
| AC-009 | Fail | Recovery can install a manifest that no longer references the verified paired backup. A duplicate blank date parameter is also accepted in request provenance. |
| AC-010 | Fail | After the recovery reproduction, offline restore of the valid prior backup fails because the committed manifest no longer lists it. |
| AC-011 | Pass | CLI help exposes the date flags; shared-entrypoint and focused suites pass reporting and restore-command checks; acquisition documentation includes the getter. |
| AC-012 | Fail | Although 121 tests pass, independent QA reproduced four adverse cases missing from that suite. The snapshot therefore does not meet the criterion for complete independent verification coverage. |
| AC-013 | Pass | The task and acquisition documentation record the user's statement of Yahoo's express prior permission and the source restriction. The statement is not independently verified. |

No criterion was blocked by environment or unavailable tooling. Seven criteria tied directly to data correctness or storage safety fail. AC-012 also fails because independent QA found untested defects. The QA evidence does not establish that Yahoo published every expected trading date; the existing CSV ends at the latest observed date, 2026-11-03.
