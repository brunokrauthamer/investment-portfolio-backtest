# Project context

## Purpose and confirmed scope

The application will help people understand how different hypothetical investment portfolios would have performed historically. The intended working MVP will calculate a backtest for a user-selected date range and show portfolio value over time, total return and maximum drawdown. Its parts will be designed and implemented incrementally with the user, beginning with obtaining data and then the frontend.

Users will select assets and their weights; the weights must sum to exactly 100%. Assets will include indices or ETFs; Ibovespa, IFIX and IVVB11 are examples, not a finalized universe. Selic will be available as an asset, and there will be no separate cash allocation option. The meaning and representation of each asset, including Selic, remain to be established when its data and calculations are designed.

Every date accepted by the system must have data for every asset. The method for aligning data and the handling of gaps are still open; do not assume that filling, dropping or rejecting observations is approved.

## Architecture and boundaries

- Use a TypeScript and React frontend and a Python backend with FastAPI, organized as a modular monolith.
- Backend Python work uses `backend/.venv` and `backend/requirements.txt` as its dependency manifest, including when there are no third-party dependencies. From the repository root, create the environment with `python -m venv backend/.venv`, install dependencies with `.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt` on Windows, and run backend Python commands through `.\backend\.venv\Scripts\python.exe` (or `backend/.venv/bin/python` on Unix). The initial environment creation uses the system Python. Update `backend/requirements.txt` whenever backend Python dependencies change; do not commit the environment itself.
- Organize backend responsibilities as sibling modules under `backend/src/`: `api` handles HTTP requests and responses, while `internet_data_getter` owns external data acquisition through safe source-file preservation. Within the getter, keep asset-specific acquisition logic together; expose explicit Python and command-line entry points. Domain logic represents portfolios and backtesting rules and remains independent of FastAPI, React, CSV layouts and data providers.
- Store initially acquired historical data in project CSV files. Storage adapters operate behind focused contracts where they clarify an actual boundary; assemble concrete dependencies at the application boundary. A relational database is not required for the MVP.
- Data acquisition belongs in `internet_data_getter`, with asset-specific code grouped together and shared code introduced for demonstrated common needs. Explicit source commands download B3's original IFIX and IBOVESPA annual CSV files for 2011 through the current year and scrape BCB's SGS 11 daily effective Selic rate into a generated CSV. Imports and application startup must not initiate network requests. Other assets and backtesting use remain unimplemented.
- Use interfaces and extension points when justified by real requirements, and keep modules and functions focused rather than anticipating deployment into services.

## Data safety and provenance

Do not overwrite or remove source data during scaffolding. Before modifying or replacing source files, create recoverable backups outside the active input location. Updates must be atomic so a failure or interruption cannot leave an active file partially written. Keep a write-ahead recovery record until active data and its provenance manifest are committed. The data implementation must document its backup location, naming convention, offline restore procedure, and prevent backup files from being treated as active inputs.

Document each dataset's origin and relevant source access and usage constraints, including for scraping. Do not fabricate historical results. The IFIX acquisition is limited to the user's stated personal use; it does not grant redistribution rights or decide future financial conventions.

## Open decisions

- Asset universe, markets, currencies, date ranges, frequency, sources, source terms and CSV schema.
- Asset-to-class mapping, fractional holdings and the precise interpretation of weights and Selic.
- Rebalancing rules and execution timing; costs, taxes, dividends, inflation, currency conversion and adjusted prices.
- The method and calendar for aligning datasets, missing observations and non-trading days, and the handling of invalid requests.
- Precise definitions of total return and maximum drawdown, chart details and other metrics.

The Selic acquisition preserves the source's daily percentage text. This does not establish how a Selic observation contributes to portfolio value or how datasets are aligned. Do not infer financial behavior from the acquired CSV; agree on those conventions before implementing calculations.
