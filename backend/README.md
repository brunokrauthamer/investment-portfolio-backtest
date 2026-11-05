# Backend

The S&P 500 getter is registered as `sp500`; it runs in the default all-getters command and can also be selected with `--getter sp500`. Use `fetch-sp500 --start-date YYYY-MM-DD --end-date YYYY-MM-DD` to supply inclusive date bounds, or call `acquire_sp500(data_dir=None, start_date=None, end_date=None)` from Python. See the [acquisition guide](src/internet_data_getter/README.md) for the default range, output, incremental merge behavior, and recovery command.

The Python/FastAPI modular monolith is planned here. Data acquisition is available as an explicitly invoked command; importing modules or starting an API must not contact data providers. Financial and backtesting behavior still requires agreement on the conventions in [project context](../docs/project-context.md).

## Normalize gathered index data

`backend.src.market_data_normalizer.indexes.gather_index_data()` reads the acquired IBOVESPA, IFIX, Selic and S&P 500 CSV files with pandas and writes `data/normalized/gathered_data.csv`. Pass a different data root to `gather_index_data(data_dir)` when needed. See the [normalizer guide](src/market_data_normalizer/README.md) for input formats, units, gaps and failure behavior.

## Acquire historical data

Set up the backend virtual environment as described in [acquisition](src/internet_data_getter/README.md). From the repository root on Windows, select Selic with --getter selic, IFIX with --getter ifix, IBOVESPA with --getter ibovespa, or S&P 500 with --getter sp500; omit --getter to run all registered getters. Use --data-dir PATH to choose another destination. The acquisition guide covers file layouts, browser setup, reruns and offline restore.
Install Google Chrome before running `.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --getter selic` from the repository root on Windows to scrape BCB SGS series 11 with Selenium. Select IFIX with `--getter ifix`, or omit `--getter` to run all registered getters. Use `--data-dir PATH` to choose another destination. The acquisition guide covers file layouts, browser and driver setup, reruns and offline restore.

## Run the API

The backend includes a small FastAPI application. From the repository root, create the virtual environment and install backend requirements once:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Start the API from the repository root on Windows:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.src.api.main:app --reload
```

Run the health and portfolio API contract tests from the repository root with:

```powershell
.\backend\.venv\Scripts\python.exe -m unittest backend.src.api.tests.test_health backend.src.api.tests.test_portfolio backend.src.api.tests.test_portfolio_calculation backend.src.api.tests.test_portfolio_result_contract -v
```

`GET http://127.0.0.1:8000/health` returns HTTP 200 with `{"status":"ok"}`. It confirms only that the API process is serving requests. Importing and starting the API do not acquire market data.

## Portfolio setup API

`GET http://127.0.0.1:8000/api/indexes` returns the supported choices in this order: `ibovespa` (IBOVESPA), `ifix` (IFIX), `selic` (Selic) and `sp500` (S&P 500).

`POST http://127.0.0.1:8000/api/portfolio` accepts an `initial_date`, `end_date`, one to four unique `allocations` containing an index ID and percentage, and a `rebalancing` value. Dates must be valid ISO calendar dates in order. Percentages must be JSON numbers with at most two decimal places and sum exactly to 100. Valid rebalancing values are `none`, `3_months`, `6_months`, `1_year`, `2_years` and `3_years`. For example:

```json
{
  "initial_date": "2020-01-01",
  "end_date": "2024-12-31",
  "allocations": [
    {"index": "ibovespa", "percentage": 40},
    {"index": "sp500", "percentage": 60}
  ],
  "rebalancing": "6_months"
}
```

The API reads `data/normalized/daily_returns_reais.csv` with pandas for each valid request. It filters the requested dates inclusively and returns one cumulative portfolio return series point per available CSV date. Each point includes UTC-midnight epoch milliseconds in `x`, cumulative percentage points in `y`, the ISO date, the day's return percentage points and the cumulative return percentage points. The first available row contributes its return. Daily portfolio returns use the weights at the start of that row, then weights drift with relative asset returns. Calendar rebalancing resets to the requested weights after the first available row on or after each anniversary; Selic compounds as a daily return like the other selected assets. A valid range with no CSV dates returns an empty `data` list. No starting currency amount is used.

Invalid requests return HTTP 422. Missing or malformed historical data and calculations that cannot continue after a total portfolio loss return HTTP 503 with a safe error detail. The route applies the same exact JSON validation when `Content-Type` is omitted or empty; `application/json` and `+json` media types are also supported, while other media types are rejected. Duplicate JSON member names, nonfinite numbers, and percentages with more than two decimal places are invalid. Importing and starting the API do not read the CSV or make network requests. The Docker Compose API service mounts the normalized CSV read-only at the expected path. The Vite development and preview servers proxy same-origin `/api` requests to `127.0.0.1:8000`. A production host must provide an equivalent same-origin reverse proxy and the normalized CSV file.
