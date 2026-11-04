# Backend

The S&P 500 getter is registered as `sp500`; it runs in the default all-getters command and can also be selected with `--getter sp500`. Use `fetch-sp500 --start-date YYYY-MM-DD --end-date YYYY-MM-DD` to supply inclusive date bounds, or call `acquire_sp500(data_dir=None, start_date=None, end_date=None)` from Python. See the [acquisition guide](src/internet_data_getter/README.md) for the default range, output, incremental merge behavior, and recovery command.

The Python/FastAPI modular monolith is planned here. Data acquisition is available as an explicitly invoked command; importing modules or starting an API must not contact data providers. Financial and backtesting behavior still requires agreement on the conventions in [project context](../docs/project-context.md).

## Acquire historical data

Set up the backend virtual environment as described in [acquisition](src/internet_data_getter/README.md). From the repository root on Windows, select Selic with --getter selic, IFIX with --getter ifix, IBOVESPA with --getter ibovespa, or S&P 500 with --getter sp500; omit --getter to run all registered getters. Use --data-dir PATH to choose another destination. The acquisition guide covers file layouts, browser setup, reruns and offline restore.
