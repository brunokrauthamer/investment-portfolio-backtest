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

`GET http://127.0.0.1:8000/health` returns HTTP 200 with `{"status":"ok"}`. It confirms only that the API process is serving requests. Importing and starting the API do not acquire market data.
