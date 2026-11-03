# Data acquisition

Acquisition runs only when explicitly invoked by a caller or operator. Python callers can use `acquire_all(data_dir)` to run all registered getters and receive a dictionary of their reports, or `acquire("ifix", data_dir)` and `acquire("selic", data_dir)` to run one getter. `data_dir` is optional in both calls. `acquire_ifix(data_dir)` and `acquire_selic(data_dir)` remain available as conveniences. `acquire_all` propagates an exception immediately and stops; incomplete reports are returned normally. Importing modules or starting the application must not make network requests.

## IFIX daily evolution

Install Python 3.9 or later. From the repository root, create the backend virtual environment and install its declared dependencies:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Run all registered getters (IFIX and Selic):

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter
```

To run one getter, add `--getter ifix` or `--getter selic` before any subcommand. The command reports failures and continues to the next getter; it exits with status 1 if any getter fails or reports an incomplete run.

The IFIX getter fetches one B3 CSV for each year from 2011 through the current year using the same annual download endpoint used by the [B3 IFIX daily-evolution page](https://sistemaswebb3-listados.b3.com.br/indexStatisticsPage/daily-evolution/IFIX?language=pt-br). The page's semester selector changes the displayed half-year; the download itself contains the full year. Files are saved as `data/ifix/source/IFIX_<year>_Evolucao_Diaria.csv`. The page returns Base64 text and the command decodes it to the original CSV bytes, including its original character encoding; it does not parse or rewrite the observations. Validation checks the year header, all 12 month columns, the 31 day rows, summary rows, and at least one observation. Blank future months in the current-year file are accepted.

The command also writes `data/ifix/manifest.json` with each year's source URL, original B3 filename, retrieval time and SHA-256 digest. It reports saved, updated and unchanged files. HTTP, format, download and storage errors are listed by year, processing continues for other years, and any incomplete run exits with status 1.

### Safe reruns and recovery

An identical download does not change the active file or create a backup. When B3 changes an existing year's file, the previous bytes are copied and hash-verified under `data/backups/ifix/<year>/` before the active file is atomically replaced. The manifest lists backup paths and hashes under that year's `previous_versions`. A write-ahead manifest entry lets the next run recover the backup reference if a process stops after replacing the active file but before committing the manifest update. If recovery cannot match the active file to the recorded old or new hash, it stops and preserves the pending entry.

To restore an earlier version without contacting B3, use a backup path listed in that year's manifest:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --data-dir data restore --year 2011 --backup backups/ifix/2011/PASTE_BACKUP_PATH_FROM_MANIFEST.csv
```

Replace the example path with the exact manifest-relative backup path for that year. The restore verifies the listed backup's hash and CSV structure, backs up and records the currently active file, then atomically installs the selected version and updates provenance. It does not redownload the newest file. A later explicit download command may update the restored version again, after preserving it as another backup. Keep backups separate from `data/ifix/source/` so they are not mistaken for active source files.

An exclusive lock prevents concurrent runs. If a process is interrupted, `.acquisition.lock` may remain under `data/ifix/`. Confirm that no acquisition process is still running before deleting this stale lock and retrying. The command never removes a lock automatically.

The acquisition makes one paced HTTPS request per requested year with certificate verification enabled. It preserves files already saved if a later year fails. The page offers years dynamically through the current year; the current year may be partial. The stored file remains B3's monthly-by-day matrix and is not converted into a normalized daily series. B3 data is retained for the user's stated personal use; data-use and access terms belong to B3 and may change.

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
