# Backend

The Python/FastAPI modular monolith is planned here. Data acquisition is available as an explicitly invoked command; importing modules or starting an API must not contact data providers. Financial and backtesting behavior still requires agreement on the conventions in [project context](../docs/project-context.md).

## Acquire historical data

Set up the backend virtual environment as described in [acquisition](src/internet_data_getter/README.md). Run `.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --getter selic` from the repository root on Windows to scrape BCB SGS series 11. Select IFIX with `--getter ifix`, or omit `--getter` to run all registered getters. Use `--data-dir PATH` to choose another destination. The acquisition guide covers file layouts, browser setup, reruns and offline restore.
