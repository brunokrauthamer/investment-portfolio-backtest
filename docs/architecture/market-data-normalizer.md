# Market data normalizer

`backend.src.market_data_normalizer.indexes` provides the explicit `gather_index_data(data_dir=None)` function. It reads the acquired IBOVESPA, IFIX, Selic and S&P 500 source files with pandas and writes the derived `normalized/gathered_data.csv` beneath the chosen data root. The default root is the repository's `data` directory and does not depend on the caller's working directory.

The service owns only local CSV layout conversion. Its B3 reader expands the annual day-by-month matrix; its daily-series reader accepts the canonical Selic and Yahoo getter schemas. The orchestration joins by source date and retains original values and units. It does not acquire data, touch backups, infer missing values, define portfolio behavior, or depend on FastAPI. Imports have no file or network side effects.

The table includes the union of dates with at least one observation and keeps missing asset cells blank. Invalid, empty, malformed or duplicate source observations stop the operation. Pandas writes a temporary file in the destination directory, and `os.replace` publishes it only after a successful write. Existing source files are read-only; the derived output is reproducible from those files.
