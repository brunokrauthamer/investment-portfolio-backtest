# Project context

## Purpose and confirmed scope

The application will help people understand how different hypothetical investment portfolios would have performed historically. The intended working MVP will calculate a backtest for a user-selected date range and show portfolio value over time, total return and maximum drawdown. Its parts will be designed and implemented incrementally with the user, beginning with obtaining data and then the frontend.

Users will select assets and their weights; the weights must sum to exactly 100%. Assets will include indices or ETFs; Ibovespa, IFIX and IVVB11 are examples, not a finalized universe. Selic will be available as an asset, and there will be no separate cash allocation option. The meaning and representation of each asset, including Selic, remain to be established when its data and calculations are designed.

Every date accepted by the system must have data for every asset. The method for aligning data and the handling of gaps are still open; do not assume that filling, dropping or rejecting observations is approved.

## Architecture and boundaries

- Use a TypeScript and React frontend and a Python backend with FastAPI, organized as a modular monolith.
- HTTP routes handle requests and responses; application services coordinate use cases; domain logic represents portfolios and backtesting rules. Keep domain logic independent of FastAPI, React, CSV layouts and data providers.
- Store initially acquired historical data in project CSV files. Storage adapters operate behind focused contracts where they clarify an actual boundary; assemble concrete dependencies at the application boundary. A relational database is not required for the MVP.
- Data acquisition is a separate responsibility. It is not yet implemented; imports and application startup must not initiate network requests.
- Use interfaces and extension points when justified by real requirements, and keep modules and functions focused rather than anticipating deployment into services.

## Data safety and provenance

Do not overwrite or remove source data during scaffolding. Before modifying or replacing source files, create recoverable backups outside the active input location. Updates must be atomic so a failure or interruption cannot leave an active file partially written. The data implementation must document its backup location, naming convention and restore procedure, and prevent backup files from being treated as active inputs.

Document each dataset's origin and relevant source access and usage constraints, including for scraping. Do not fabricate historical results. The user declined synthetic sample data; obtain real data in a future agreed step.

## Open decisions

- Asset universe, markets, currencies, date ranges, frequency, sources, source terms and CSV schema.
- Asset-to-class mapping, fractional holdings and the precise interpretation of weights and Selic.
- Rebalancing rules and execution timing; costs, taxes, dividends, inflation, currency conversion and adjusted prices.
- The method and calendar for aligning datasets, missing observations and non-trading days, and the handling of invalid requests.
- Precise definitions of total return and maximum drawdown, chart details and other metrics.

Do not infer these decisions from examples or implement financial behavior until the user has agreed on the relevant conventions.
