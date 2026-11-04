# Market data normalizer

The indexes service combines the existing source CSVs without making network requests. From the repository root, run:

```powershell
.\backend\.venv\Scripts\python.exe -c "from backend.src.market_data_normalizer.indexes import gather_index_data; print(gather_index_data())"
```

Or call the function from Python:

```python
from backend.src.market_data_normalizer.indexes import gather_index_data

output_path = gather_index_data()
```

The function returns the path to `data/normalized/gathered_data.csv`. To use a different root containing the per-index source folders, pass that data directory, for example `gather_index_data(Path("/tmp/my-data"))`.

The service reads all direct `*.csv` files inside `ibovespa/source`, `ifix/source`, `selic/source` and `sp500/source`. B3's annual matrix is expanded into observations by its year, day and Portuguese month columns. The Selic and S&P 500 inputs use the acquired `date,rate_percent_per_day` and `date,adjusted_close` columns. Backup directories and nested folders are not inputs.

The output columns are `date,ibovespa,ifix,selic,sp500`. Dates use ISO `YYYY-MM-DD` and rows are sorted in ascending order. Values retain their source meaning and precision: IBOVESPA and IFIX index levels, BCB's daily Selic rate in percent per day, and Yahoo's S&P 500 adjusted close. Brazilian B3 thousands separators and decimal commas become ungrouped values with a decimal period. The service does not convert these values into a shared unit or calculate returns.

The output contains the union of source observation dates. When an asset has no observation on one of those dates, its cell is empty. No dates or values are interpolated or fabricated. A missing source dataset, empty file, incompatible schema, invalid date or value, or duplicate date for the same asset raises `NormalizationError` before publication. The output is staged with pandas in its destination directory and atomically replaced after a complete run, so a failed read or write leaves the previously published file intact. Source CSVs are read only. The generated table can be recreated from those source files.

The service uses pandas for CSV reading and writing. Install it with the rest of the backend dependencies from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```
