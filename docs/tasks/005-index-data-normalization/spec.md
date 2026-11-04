# Index data normalization — specification s001 (proposed)

## Goal and scope

Provide a callable Python service under `backend/src/market_data_normalizer/indexes` that gathers the existing IBOVESPA, IFIX, Selic and S&P 500 source CSVs into `data/normalized/gathered_data.csv`. All CSV reading and writing in the service uses pandas. This specification and its choices are proposed for human approval; no implementation is approved yet.

## Proposed conventions

- Include every date that has at least one source observation. Put an empty cell where an asset has no observation on that date; never fill, interpolate, drop dates solely for gaps, or invent observations. This output convention does not decide how a future backtest handles missing dates.
- Date strings are ISO `YYYY-MM-DD`. Use UTF-8, comma-delimited CSV, decimal periods and no thousands separators. Preserve all source decimal digits, without rounding or binary floating-point conversion. For example, B3 `187.952,91` becomes `187952.91` and Selic `0.040239` remains `0.040239`.
- IBOVESPA and IFIX retain B3's daily index levels; Selic retains BCB SGS 11's daily percentage rate (not an accumulated return); S&P 500 retains Yahoo's adjusted close. This is a common table, not a conversion to a common financial unit or return series.
- Read all direct `*.csv` children of each of `data/ibovespa/source`, `data/ifix/source`, `data/selic/source`, and `data/sp500/source`; do not read backups or nested directories. Parse B3's annual day-by-month matrix, using the year in its index header and ignoring summary rows. Selic uses `date,rate_percent_per_day`; S&P 500 uses `date,adjusted_close`.
- Each asset must have at least one input file and at least one observation; fail clearly if a file is unreadable, malformed, contains an invalid observation/date, or has a duplicate date for the same asset across or within files. Do not silently choose between duplicate observations. An empty B3 day/month cell is absence, including blank impossible calendar dates and future months; a populated impossible date fails.
- An explicit function call writes the output; imports do not write files or contact the network. An optional data directory argument is a local root override, defaulting to the repository `data` directory independently of the process working directory. A successful rerun replaces the generated file atomically; failures leave any existing output intact. Source files are never modified.

## Acceptance criteria

- **AC-001 — Inputs and isolation:** Read every direct CSV in the four named source folders with pandas, applying the source-specific schemas above, and leave source files unchanged. No network, source downloads, backtesting, portfolio or investment calculations.
- **AC-002 — B3 transformation:** Convert B3 annual day/month observations to real calendar dates and normalized numeric text, without using summary rows. Retain each actual observation once, including leap days, and reject a populated invalid calendar date or invalid numeric value.
- **AC-003 — Other source values:** Preserve all Selic `rate_percent_per_day` and S&P 500 `adjusted_close` observations and their displayed precision, using their own source dates and the stated units. Validate dates and numeric text.
- **AC-004 — Table and gaps:** The output has exactly `date,ibovespa,ifix,selic,sp500` in that order, one row per date in the union of observed dates, strictly ascending ISO dates and blank cells for missing asset observations. It contains no extra dates or derived values.
- **AC-005 — Invocation and dependency:** A documented callable `gather_index_data(data_dir=None)` creates `normalized/gathered_data.csv` under the selected root and returns its `Path`; default to repository data. Declare pandas in `backend/requirements.txt`. CSV interactions in the service use pandas. No side effects on import.
- **AC-006 — Errors and safe output:** Missing/empty datasets, incompatible schemas, malformed dates/values and same-asset duplicate dates fail explicitly before publication; errors identify the input/asset and reason. Publication stages the CSV in the destination directory and atomically replaces the output; failure leaves any previously published output intact and cleans up temporary output where possible.
- **AC-007 — Delivery:** Document setup, function call, input and output layout, units, missing values, and failure behavior. Exercise the function on the repository data after successful offline verification, producing the requested output. Independent review and QA assess the integrated snapshot; no browser is needed for this non-web service.

## Boundaries and uncertainties

No new data acquisition, API, command-line interface, currency conversion, portfolio or return computation is included. The output is reproducible derived data, not an acquired source file; source provenance remains in the existing manifests. Direct-child globbing matches the requested folders; recursive discovery would require a separate decision. These proposed data choices need the user's agreement before implementation.
