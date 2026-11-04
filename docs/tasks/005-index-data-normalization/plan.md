# Index data normalization — correction plan p002 (proposed)

Approved specification [s001](spec.md), SHA-256 `b3b547784fd28f8ac76162b9913d1879c99f8ef51c4e4e5576505e5fcb13a3b8`, remains the acceptance contract. This revision amends the [approved initial plan p001](history/plan-p001.md) for correction cycle 1. The initial cycle used all three implementation rounds. This plan requires explicit approval before correction code is written.

## Diagnosis and repair boundary

Independent review and QA reproduced REV-005 under AC-006 on snapshot `916023ebac0fc2ce8e6c00e494598ad3bf05d339:sha256:dbfedb6c148b366991c74f8180eda14743d7adb5c17cf97015674dccbd9a8316`. A date-only Selic record passes the column and index checks in `read_daily_series`. The pandas Python engine pads the omitted value with `None`, and `_decimal_text` calls `.strip()` on it. The existing output survives, but the caller receives an `AttributeError` without the source path or the malformed row. The same reader handles S&P 500.

Add a missing-field check to the shared daily reader after the schema checks and before date or decimal validation. Use pandas to detect padded fields and raise `NormalizationError` identifying the source path, the malformed data row, and the expected two fields. A present empty field continues through the existing date or value validation. This keeps record-width validation at the reader boundary and retains the existing pandas parser, decimal precision, public function and atomic publication behavior.

## Ordered work and evidence

1. After approval, dispatch `developer-correction` with `feature-tdd`, scoped to the daily reader, focused tests and task evidence. Add regression coverage through `gather_index_data` for a date-only record after a valid row in both Selic and S&P 500. Create inputs with pandas, publish a baseline first, then append the short record. Assert a contextual `NormalizationError` with path, row and expected width, and compare the previous output with pandas after rejection. Observe the targeted cases fail before editing the reader.
2. Add the width check, observe the regressions pass, and run `.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/src/market_data_normalizer/indexes/tests -v` plus `git diff --check`. Exercise the documented function against the repository data and compare output with all four input sets using pandas. Check that source files are intact and that existing documentation still describes the behavior. Record commands, results and the integrated snapshot.
3. Have a fresh reviewer assess the integrated correction against s001 and p002, including REV-005 and the earlier malformed-input findings. After review passes, have fresh independent QA verify all acceptance criteria and the corrected failure paths on the same snapshot. Capture matching before and after snapshot digests for each evaluation. The getter regression suite has a separately recorded dependency blocker (`beautifulsoup4` and package-index access). Run it if the environment supports it, and keep any unresolved limitation explicit. This backend service has no browser scenario.
4. Audit the current review and QA results, evidence, open findings and limits before asking for final approval. Correction rounds are tracked separately, with up to three implementation and review rounds. If review exhausts them or correction QA finds an implementation defect, record the evidence and return for human intervention.

Evidence for the diagnosis is in the [round 3 review](review.md) and [independent QA assessment](verification.md).
