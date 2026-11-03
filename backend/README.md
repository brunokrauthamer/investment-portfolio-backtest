# Backend

The Python/FastAPI modular monolith is planned here. Data acquisition is available as an explicitly invoked command; importing modules or starting an API must not contact data providers. Financial and backtesting behavior still requires agreement on the conventions in [project context](../docs/project-context.md).

## Download IFIX source files

Set up the project virtual environment as described in [acquisition](src/internet_data_getter/README.md), then run `.venv\Scripts\python -m backend.src.internet_data_getter` from the repository root on Windows. This downloads B3's annual IFIX daily-evolution CSV files from 2011 through the current year into `data/ifix/source/`. Use `--data-dir PATH` to choose another destination. The acquisition guide also covers the file layout, rerun behavior, and restore steps.
