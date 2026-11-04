# Daily returns in reais — verification

## TDD and implementation — s001 / p001, initial round 1

The initial test-first check used the daily-return API scaffold, which wrote only the requested output header. The focused example fixture then failed on the expected observable result:

- Command: `\.\backend\.venv\Scripts\python.exe -m unittest backend.src.market_data_normalizer.tests.test_daily_returns.DailyReturnsTests.test_handles_user_example`
- Actual red result: `FAIL: test_handles_user_example`; `AssertionError: 0 != 1` at the assertion for one expected return row. This demonstrated that the service did not yet produce the requested result.
- After implementing the service, the 10 focused tests passed, covering the user's numeric example, sparse IBOVESPA/IFIX/Selic values, S&P/FX compounding across an S&P gap, missing currency fallback, staggered starts, multiple currency files, validation, import side effects, default root and atomic replacement.
- The first implementation run also exposed a Python 3.9 import error from runtime evaluation of `float | None` annotations. The module now defers annotation evaluation, and the same public API imports exercised by the focused suite pass in the project Python 3.9 environment.

## Integrated checks

| Check | Command | Observed result |
| --- | --- | --- |
| Daily return service | `\.\backend\.venv\Scripts\python.exe -m unittest backend.src.market_data_normalizer.tests.test_daily_returns` | 10 tests passed. |
| Existing index normalizer | `\.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/src/market_data_normalizer/indexes/tests` | 12 tests passed. |
| Existing API tests | `\.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/src/api/tests` | 2 tests passed. |
| Existing data-getter suite | `\.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/src/internet_data_getter/tests` | 123 tests ran; 6 failed in unrelated S&P 500 pagination rejection tests (`test_parser_rejects_detectable_pagination`, `test_parser_rejects_document_next_link_metadata`, `test_parser_rejects_next_links_and_pagination_on_no_data_pages`). This suite failure is recorded for independent review; it was not baseline-tested during this task. |
| Whitespace check | `git diff --check` | Passed. |

The backend environment was created at `backend/.venv` and dependencies from `backend/requirements.txt` were installed. The Internet Data Getter failures are not attributed to this change; their baseline status remains unknown.

## Generated project data

Ran `\.\backend\.venv\Scripts\python.exe -c "from backend.src.market_data_normalizer.daily_returns import generate_daily_returns_reais; print(generate_daily_returns_reais())"`. It generated `data/normalized/daily_returns_reais.csv` with columns `date,ibovespa,ifix,selic,sp500`, 4,085 rows, no blank cells, and ascending dates. SHA-256: `1303288d45ed81dc57ead5f713800f53be1e72b40f74c70aac99f5894068fb80`.

The output for 2011-01-04 was IBOVESPA `0.0050808778210897`, IFIX `-0.0085405200227748`, Selic `0.00040203`, and S&P 500 in reais `0.0071786931127815`, matching the specified example within floating-point precision. The 2011-03-09 IBOVESPA and IFIX returns use their last prior available observations after the 2011-03-07/08 blanks. The 2026-11-04 S&P calculation uses the latest earlier USD/BRL observation.

SHA-256 checks confirm `data/normalized/gathered_data.csv` and `data/dolar/source/USD_BRL Dados Históricos (1).csv` still match their baseline snapshot hashes. No network request was made by the service.

Evidence files: `evidence/baseline-snapshot.json` and `evidence/implementation-round-1-snapshot.json`.

## Independent QA — s001 / p001

Environment: Windows, project `backend/.venv`, Python 3.9, pandas 2.3.3. QA ran offline. The before and after working-tree snapshots both identify `4371d83c90b5306b05eef12ee7395e2912dce711:sha256:47883fbe00c2ccf93be3192f2af4cf7e44b4204fdd9135ba9127b3c245aacfc2`; no implementation or source data changed during QA. See `evidence/qa-before.json`, `evidence/qa-after.json`, `evidence/qa-independent-output.txt`, and `evidence/qa_independent.py`. The lead corrected a transcription error in this identifier during the final audit; the underlying snapshot files were unchanged.

| Criterion | Expected | Observed | Result |
| --- | --- | --- | --- |
| AC-001 | Output has exactly the five requested columns, ISO gathered dates after the first row, unique and ascending, without currency-only dates; returns are numeric. | Independently parsed all inputs and output. The file contains 4,085 rows and exactly those columns, with matching dates, no blanks and unique ascending dates. Compared all 16,340 returns using a separate Decimal implementation; maximum absolute difference was 4.63e-16. | Pass |
| AC-002 | Missing index observations are zero and do not reset the last available index level. 2011-03-07/08 are zero; 2011-03-09 uses 2011-03-04. | Both 2011-03-07 and 2011-03-08 returned zero for IBOVESPA and IFIX. On 2011-03-09, returns were -0.011003189138403369 and 0.001188613086630097; these match the independent calculation from the most recent prior observations. Sparse fixture also passed. | Pass |
| AC-003 | Selic percent per day is divided by 100; blanks yield zero. | 2011-01-04 returned 0.00040203000000000005; an isolated fixture confirmed 5 -> 0.05 and blank -> 0. | Pass |
| AC-004 | S&P and FX growth factors are compounded. Missing S&P is zero, FX baseline stays tied to the prior S&P observation, and same-day missing FX uses the last available rate. | 2011-01-17 S&P return was zero despite FX presence; 2011-01-18 resumed at -0.005398100662605709 and matched the independent Decimal calculation. An isolated fixture checked an FX move during an S&P gap and missing current-day FX. 2026-11-04 same-day FX fallback returned 0.017425207295096223 and matched calculation. | Pass |
| AC-005 | The supplied example reproduces its four returns. | 2011-01-04 produced IBOVESPA 0.005080877821089791, IFIX -0.008540520022774833, Selic 0.00040203000000000005 and S&P 0.00717869311278152. All are within the requested numerical tolerance. | Pass |
| AC-006 | Missing history yields zero until calculable. Malformed, invalid, duplicate, unsorted or missing inputs are rejected without replacing an existing output; valid blanks remain accepted; output publication is safe. | Isolated fixtures covered staggered first observations, unavailable earlier FX, gaps, explicit blanks, both underwidth row forms, invalid/duplicate dates, incompatible schemas and missing gathered/currency files. Every rejected-input case preserved sentinel output bytes. The focused test also simulated atomic `os.replace` failure and confirmed the prior output remained intact and the temporary file was cleaned up. Source hashes remained gathered `3fb8c707d7800e602672c90a83108704d518680af631b87e595a3e8281cfdfbe` and currency `1a1dc1c1f78892d8ac29ff5076d350cfc16aeda57cc82585cd507450b49d51dd`; generated output SHA-256 is `1303288d45ed81dc57ead5f713800f53be1e72b40f74c70aac99f5894068fb80`. | Pass |
| AC-007 | Explicit Python entry point accepts optional root, default root does not depend on current directory, imports have no data/network side effects, and docs describe the interface and rules. | Called the no-argument service from a temporary working directory with socket connections disabled; it returned the repository output path and regenerated identical bytes. Import left the source and output hashes unchanged. Inspected the README and architecture doc for command, schema, formulas, gaps and validation behavior. | Pass |

Commands and evidence: `evidence/qa-focused-tests.txt` (12 daily-return tests passed), `evidence/qa-index-tests.txt` (12 existing index tests passed), `evidence/qa-api-tests.txt` (2 API tests passed), and `evidence/qa-diff-check.txt` (`git diff --check` passed). The independent project data and fixture checks were run with `backend/.venv/Scripts/python.exe evidence/qa_independent.py`; results are in `evidence/qa-independent-output.txt`. Browser checks are not applicable to this local Python service. No unresolved implementation defect or specification ambiguity was found.

## Review repair — s001 / p001, initial round 2

The initial round's recorded behavioral red was limited to the example fixture. The independent reviewer also observed a distinct underwidth-row defect; no earlier red evidence for that defect is claimed. For REV-001, I added separate regressions for an underwidth gathered row and an underwidth currency row while retaining explicit blank fields as valid observations. Both tests failed before the repair with the observed `AttributeError` and preserved the previous output; see `evidence/tdd-red-underwidth-round-2.txt`.

The service now distinguishes pandas' missing-cell `None` from an explicitly blank string. Missing cells raise the public `NormalizationError` with the source path, row number and field name; blank strings remain valid missing observations. The two new regression tests pass after the fix. The currency order regression uses files whose lexical file order is opposite their dates and confirms date-based sorting for lookup.

| Check | Command | Observed result |
| --- | --- | --- |
| Daily returns, including REV-001 regressions and reverse currency order | `\.\backend\.venv\Scripts\python.exe -m unittest backend.src.market_data_normalizer.tests.test_daily_returns` | 12 tests passed. |
| Existing index normalizer | `\.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/src/market_data_normalizer/indexes/tests` | 12 tests passed. |
| Existing API tests | `\.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/src/api/tests` | 2 tests passed. |
| Whitespace check | `git diff --check` | Passed. |
| Generated project data | Daily-return generation command | Regenerated output is byte-identical to the round 1 artifact (same SHA-256: `1303288d45ed81dc57ead5f713800f53be1e72b40f74c70aac99f5894068fb80`). |

The reviewer confirmed the six getter-suite pagination failures also occur at baseline, so they are outside this feature's changed files. This repair pass did not rerun that suite. Evidence: `evidence/review-initial-1-getter-baseline.txt`.

## Lead final audit — 2026-11-04

The current [audit snapshot](evidence/final-audit-snapshot.json) matches the round 2 review and independent QA snapshot, and specification and plan hashes still match the user's recorded approval. Review and QA passed on the same snapshot; AC-001 through AC-007 all passed, the two review findings are resolved, and there are no active assignments. The README and architecture changes were part of that reviewed snapshot. The delivered CSV has SHA-256 `1303288d45ed81dc57ead5f713800f53be1e72b40f74c70aac99f5894068fb80`.

Limitations for final human review: initial implementation recorded a behavioral red for the example but did not record separate observed behavioral reds for every initial behavior as required by the feature-tdd skill; those missing observations cannot be reconstructed. Both later underwidth regressions did have recorded red and green results. Independent review and QA verified the resulting behavior. Six S&P pagination failures in the broader getter suite also reproduced on baseline in the same environment; they are outside this feature.
