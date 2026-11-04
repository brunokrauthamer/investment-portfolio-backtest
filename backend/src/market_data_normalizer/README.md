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

## Daily returns in reais

After generating `normalized/gathered_data.csv`, run the daily return service from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -c "from backend.src.market_data_normalizer.daily_returns import generate_daily_returns_reais; print(generate_daily_returns_reais())"
```

The function returns the path to `normalized/daily_returns_reais.csv`. It accepts an optional data root with the same folders as the gather service. It reads the gathered data and the direct CSV files under `dolar/source/`; it does not acquire or modify source data. Imports have no file or network side effects.

The output has columns `date,ibovespa,ifix,selic,sp500` and includes the gathered dates after the first row. Dates remain in ascending ISO format and returns are decimal values. IBOVESPA and IFIX returns divide the current level by the most recent prior available level and subtract one; missing index observations output zero and do not reset the baseline. Selic values are divided by 100, while missing observations output zero.

For S&P 500, the service multiplies the S&P growth factor by the USD/BRL growth factor and subtracts one. It uses the latest earlier S&P observation for the index baseline and the currency price associated with that observation for the FX baseline. At each gathered date it uses that day's currency price or the latest earlier price. Missing S&P observations output zero and do not reset either baseline, so the next S&P return includes intervening currency movement. If either necessary S&P level or currency price is unavailable, the return is zero until a calculation is possible.

Gathered data dates must be valid, unique and ascending. Currency dates must be valid and unique but may appear in any row order; the service matches them by date. It rejects missing or malformed files, incompatible headers, invalid or non-finite values, and nonpositive index or currency levels. It stages the output beside its destination and atomically replaces the prior output only after a successful calculation and write. Re-run the explicit command to recreate the derived file after updating gathered or currency source data.
