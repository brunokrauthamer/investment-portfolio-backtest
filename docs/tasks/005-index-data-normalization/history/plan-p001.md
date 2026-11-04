# Index data normalization — plan p001 (proposed)

Proposed specification: s001. Neither revision has been approved.

## Architecture

Add a small sibling `market_data_normalizer/indexes` Python package with a public `gather_index_data(data_dir=None)` function. A focused B3 reader transforms the annual matrix; a focused tabular reader handles the two existing date/value schemas. Both use `pandas.read_csv` and produce date/value frames with validated source decimal strings. Concatenate files by asset, reject duplicate dates, then outer-join the four frames, order dates, and publish with pandas `to_csv` into a temporary sibling followed by atomic replacement. Use string-preserving decimal normalization to avoid precision loss; no general-purpose plugin framework or storage abstraction is justified for these four known sources. Resolve the default root from the package location, not the caller's current directory. Do not modify the acquisition service or source data.

## Ordered work

1. Record exact human approval and baseline snapshot; dispatch a bounded implementation pass to the configured developer using the feature-tdd skill, with sole writer ownership for assigned task records.
2. Add meaningful behavior tests before implementation covering B3 matrices, date/number conversion, precision, multiple files, date union/gaps/sorting, malformed data and duplicate/missing datasets, safe replacement and import isolation; observe red then green under the backend environment. Use controlled fixtures that are not represented as real market data.
3. Implement the readers, orchestration and atomic output, declare pandas, and document setup and use. Run the relevant offline checks and run the documented function on the repository data to generate the requested artifact, preserving the input files.
4. Capture the integrated snapshot. Obtain independent reviewer examination and QA of every criterion and adverse case; follow the workflow's bounded repair and correction rules. No browser scenario applies.
5. Audit source integrity, actual output schema and representative values using pandas, documentation, evidence freshness, remaining findings and final snapshot; request explicit final approval when all required checks pass.

## Risks and verification

B3 uses a day/month matrix with locale-formatted index values; misreading month/day positions or a decimal separator changes financial data. Verify expected observations from controlled fixtures and inspect actual source/output correspondence with pandas. Multiple files can overlap; reject duplicate dates to avoid silently choosing a value. A Selic percentage rate and index levels are different units; retain the source values and describe them. Missing or malformed files must not produce a plausible partial output, and failed writes must leave the old output intact.

This machine has Python 3.9.4 and a local ignored `backend/.venv` created for discovery with access to system pandas 1.3.5. The developer must declare a compatible pandas dependency and follow the backend environment conventions. Source data can change separately from code, so QA should report the snapshot and actual input state used. No live network access is necessary.
