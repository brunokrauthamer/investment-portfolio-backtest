# Data acquisition

Acquisition runs only when explicitly invoked by a caller or operator. Python callers can use `acquire_all(data_dir)` to run all registered getters and receive a dictionary of their reports, or `acquire("ifix", data_dir)`, `acquire("ibovespa", data_dir)`, `acquire("selic", data_dir)` or `acquire("sp500", data_dir)` to run one getter. `data_dir` is optional in all calls. `acquire_ifix(data_dir)`, `acquire_ibovespa(data_dir)` and `acquire_selic(data_dir)` remain available as convenience functions; `acquire_sp500(data_dir=None, start_date=None, end_date=None)` accepts optional inclusive `YYYY-MM-DD` bounds. The S&P 500 CLI also provides `fetch-sp500 --start-date YYYY-MM-DD --end-date YYYY-MM-DD`. `acquire_all` propagates an exception immediately and stops; incomplete reports are returned normally. Reports include saved, updated, unchanged and failed items where applicable. Importing modules or starting the application must not make network requests.

## B3 annual daily evolution

Install Python 3.9 or later. From the repository root, create the backend virtual environment and install its declared dependencies:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Run all registered getters (IFIX, IBOVESPA, Selic and S&P 500):

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter
```

To run one getter, select it before any subcommand with `--getter ifix`, `--getter ibovespa`, `--getter selic` or `--getter sp500`. The default all-getters command reports failures and continues to the next getter; it exits with status 1 if any getter fails or reports an incomplete run. Use the dedicated `fetch-sp500` command when supplying S&P 500 date bounds.

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --getter ibovespa
```

Use `--getter ifix` to run only IFIX. Use `--getter sp500` to run S&P 500 with its default date range, or `fetch-sp500 --start-date 2011-01-03 --end-date 2026-11-04` to choose inclusive dates explicitly.

The IFIX getter fetches one B3 CSV for each year from 2011 through the current year using the annual download endpoint used by the [B3 IFIX daily-evolution page](https://sistemaswebb3-listados.b3.com.br/indexStatisticsPage/daily-evolution/IFIX?language=pt-br). The page's semester selector changes the displayed half-year; the download itself contains the full year. Files are saved as `data/ifix/source/IFIX_<year>_Evolucao_Diaria.csv`. The page returns Base64 text and the command decodes it to the original CSV bytes, including its original character encoding; it does not parse or rewrite the observations. Validation checks the year header, all 12 month columns, the 31 day rows, summary rows, and at least one observation. Blank future months in the current-year file are accepted.

The IBOVESPA getter uses the same B3 annual download endpoint with index code `IBOV`, language `pt-br`, and the selected year. It runs explicitly with `--getter ibovespa`, or as part of the default all-getters command. On 2026-11-03, the B3 page selector showed years 2011 through 2026, and the selected-year page displayed a 31-day matrix with Portuguese month names and minimum/maximum summary rows. The annual proxy response was HTTP 200 `text/plain; charset=utf-8` containing Base64; the decoded CSV bytes use CP1252 and begin with `IBOV - <year>`. Validation checks that header, all 12 month columns, all 31 correctly numbered rows with 13 columns, two complete nonnumeric summary rows with 13 columns, and at least one observation. The current-year export can contain blank future months. The page's visible download anchor resolves to an HTML route when requested without the page selection context, so the getter calls the observed annual proxy endpoint directly. The page's public JavaScript saves the selected annual file as `Evolucao_Diaria.csv`; the manifest retains that original filename.

IBOVESPA source files are saved as `data/ibovespa/source/IBOVESPA_<year>_Evolucao_Diaria.csv`, with provenance in `data/ibovespa/manifest.json`. Changed files are backed up under `data/backups/ibovespa/<year>/`; unchanged files retain their modification time. Backups can be restored offline using `restore-ibovespa` (details below).

The B3 getters share atomic file writes, manifest checks, backups and recovery through `internet_data_getter/b3_storage.py`. Each asset supplies its own identity, filename, source URL and CSV validator, so paths and manifests remain separate.

The command writes a separate manifest for each getter (`data/ifix/manifest.json` or `data/ibovespa/manifest.json`) with each year's source URL, original B3 filename, retrieval time and SHA-256 digest. It reports saved, updated and unchanged files. HTTP, format, download and storage errors are listed by year, processing continues for other years, and any incomplete run exits with status 1.

### Safe reruns and recovery

An identical download does not change the active file or create a backup. When B3 changes an existing year's file, the previous bytes are copied and hash-verified under `data/backups/<asset>/<year>/` before the active file is atomically replaced. Each manifest lists backup paths and hashes under that year's `previous_versions`. A write-ahead manifest entry lets the next run recover the backup reference if a process stops after replacing the active file but before committing the manifest update. If the first manifest write fails before replacement, the store removes that operation's backup only after confirming the active bytes are unchanged and the on-disk manifest does not reference it. If recovery cannot match the active file to the recorded old or new hash, it stops and preserves the pending entry.

To restore an earlier version without contacting B3, use a backup path listed in that year's manifest:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --data-dir data restore --year 2011 --backup backups/ifix/2011/PASTE_BACKUP_PATH_FROM_MANIFEST.csv
```

Replace the example path with the exact manifest-relative backup path for that year. The restore verifies the listed backup's hash and CSV structure, backs up and records the currently active file, then atomically installs the selected version and updates provenance. It does not redownload the newest file. A later explicit download command may update the restored version again, after preserving it as another backup. Keep backups separate from `data/ifix/source/` so they are not mistaken for active source files.

For IBOVESPA use its separate command, manifest backup reference, and source directory:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --data-dir data restore-ibovespa --year 2011 --backup backups/ibovespa/2011/PASTE_BACKUP_PATH_FROM_MANIFEST.csv
```

Only restore a manifest-listed path from `data/ibovespa/manifest.json`. This operation does not contact B3. Keep these backups separate from `data/ibovespa/source/`.

Each getter uses its own exclusive lock, so running one asset does not change the other's files. If a process is interrupted, `.acquisition.lock` may remain under that asset directory. Confirm that no acquisition process is still running before deleting that stale lock and retrying. Commands never remove a lock automatically.

The acquisition makes one paced HTTPS request per requested year with certificate verification enabled. It preserves files already saved if a later year fails. The page offers years dynamically through the current year; the current year may be partial. The stored file remains B3's monthly-by-day matrix and is not converted into a normalized daily series. B3 data is retained for the user's stated personal use; data-use and access terms belong to B3 and may change.

## Yahoo Finance S&P 500 adjusted-close history

The `sp500` getter retrieves daily history for Yahoo's S&P 500 symbol `^GSPC`. Yahoo's history page identifies a Date column and a separate Adj Close column; the getter preserves only these two fields in ascending order. Yahoo describes Adj Close as adjusted for splits and dividend or capital-gain distributions. This source value does not establish a portfolio return or turn the S&P 500 price index into a total-return series.

Yahoo's [terms of service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) say automated data collection requires express prior permission. The user stated: “I have Yahoo’s express prior permission for automated collection.” Treat that as the user's statement; the getter must not bypass access controls. The permission statement does not grant data redistribution rights. Review current Yahoo terms and the scope of the permission before changing the access or use.

Run the full default range, starting on 2011-01-03 and ending on the current local calendar date:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --getter sp500
```

Choose inclusive dates in `YYYY-MM-DD` form with the dedicated subcommand:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --data-dir data fetch-sp500 --start-date 2011-01-03 --end-date 2026-11-04
```

The dates become Unix seconds for midnight UTC at the selected start and midnight UTC after the selected end, so the requested end date is included. Reversed or invalid dates fail before a source request. The Yahoo page is requested with daily interval and adjusted-close data; the parser checks the symbol, table columns, response structure, dates, adjusted prices, duplicates, range boundaries and visible pagination. It rejects unrecognized empty pages or detectable partial results. Trading days absent from the source are not synthesized. Yahoo's HTML or access conditions can change, and even a structurally valid response cannot prove that the source published every market observation.

The active file is `data/sp500/source/sp500_yahoo.csv`, with header `date,adjusted_close`, ISO dates and UTF-8 encoding. Thousands separators are removed; displayed decimal precision is preserved without rounding or scaling. `data/sp500/manifest.json` records the source symbol and URL, requested date windows and bounds, retrieval time, observed coverage/count, CSV SHA-256 and backup references.

### Incremental updates and recovery

On the first run, the selected range is downloaded. On later runs, the getter fetches an earlier prefix when the chosen start predates the saved file and a later suffix when the chosen end exceeds the saved latest observation. The suffix starts with the latest saved date, so that one value can be refreshed; a different value for an older observation stops the update. A narrower request never deletes stored rows. A subset that is already covered and ends before the latest saved date needs no source request. Older provider corrections and gaps inside the saved date span are not discovered automatically.

Changed data is committed with paired, hash-verified CSV/manifest backups under `data/backups/sp500/`, outside the active source directory. The asset uses an exclusive `.acquisition.lock`, atomic file replacement and `.pending-update.json` write-ahead recovery. Interrupted operations are recovered only when the active CSV and manifest match recorded transaction hashes; an unknown state is preserved for inspection. Identical data leaves the CSV bytes and modification time unchanged and makes no backup. Backups must never be loaded as active data.

Restore only a paired version listed in `data/sp500/manifest.json` and do so without contacting Yahoo:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --data-dir data restore-sp500 --backup backups/sp500/PASTE_LISTED_BACKUP_FILENAME.csv
```

Replace the example with the exact manifest-listed CSV backup path. Restore verifies both backup hashes and the CSV/manifest pair, preserves the current active version, and records the restore time. If `.acquisition.lock` remains after interruption, confirm no acquisition or restore is running before deleting the stale lock.


## Tests

From the repository root, run the module tests without contacting data providers:

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/src/internet_data_getter/tests
```

## Selic daily effective rate (SGS 11)

Use `--getter selic` to run only the BCB browser scraper:

```powershell
.\backend\.venv\Scripts\python.exe -m playwright install chromium
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --getter selic
```

Playwright is declared in `backend/requirements.txt`; install its matching Chromium browser after installing Python requirements. The command opens the BCB [SGS series 11 chart](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarGraficoPorId&hdOidSeriesSelecionadas=11), verifies that the source identifies daily Selic in `% p.d.`, sets the start filter to 01/01/2011 and the end filter to the latest date shown by the chart, waits for the static-chart iframe form, and confirms the chart refresh POST before opening “View values from chart”. It follows every `Next` page and requires both the reported row count and the end of pagination. It also checks the exact series code in the selected-series metadata and data-column header, date order and latest-value coverage. Date-like malformed rows with numeric rates are rejected rather than skipped as page structure. A source error or incomplete table produces a nonzero CLI result and does not replace the active CSV.

The generated `data/selic/source/selic_sgs_11.csv` has columns `date,rate_percent_per_day`, ISO dates and the source's percentage text with a decimal period. For example, the displayed `0,040239` becomes `0.040239`; the value is not divided by 100, rounded or annualized. Only source-published observations are included. `data/selic/manifest.json` records source URL, SGS code, unit, access time, selected and observed coverage, counts, CSV hash and flat paired-backup references. Each prior manifest is kept alongside its CSV backup and retains that version's source provenance. BCB lists an ODbL license on its [dataset page](https://dadosabertos.bcb.gov.br/dataset/11-taxa-de-juros---selic); check the source for current usage terms.

Before returning `unchanged`, recovering a transaction or restoring a backup, the store validates required source provenance against the matching CSV hash, counts and date coverage. When the observation bytes are unchanged, the CSV and its modification time remain untouched and no backup is made. On a changed run, the previous CSV and manifest are copied and hash-verified under `data/backups/selic/` before the new CSV is installed atomically. The `.pending-update.json` write-ahead record allows the next explicit run or restore to finish or safely roll back an interrupted update. Recovery checks the CSV and manifest together against recorded transaction states; unknown or ambiguous files leave both the manifest and pending record untouched. The exclusive `.acquisition.lock` prevents overlapping acquisitions/restores. If a process is interrupted, verify that no getter is active before removing this stale lock and retrying. Backups stay outside `selic/source/` and are never loaded as active data.

To restore a verified CSV backup offline, pass its manifest-listed relative `csv_path` or paired `manifest_path` to the dedicated command:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --data-dir data restore-selic --backup backups/selic/PASTE_BACKUP_NAME_FROM_MANIFEST
```

Restore validates the paired CSV and manifest hashes, preserves the current active version, and commits the restored observations and source provenance without a source request. It retains the original `retrieved_at` value and records the local restore time separately as `restored_at`. Do not edit `data/selic/manifest.json` or active files manually; if recovery cannot match the old, new or already-rolled-back state, preserve the files and inspect the pending record and backups.

The offline tests use controlled fixture observations and never fabricate or contact market data. Run all getter tests from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/src/internet_data_getter/tests
```
