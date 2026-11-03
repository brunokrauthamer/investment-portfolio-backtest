# Data acquisition

Acquisition runs only when explicitly invoked by a caller or operator. Python callers can use `acquire_all(data_dir)` to run all registered getters and receive a dictionary of their reports, or `acquire("ifix", data_dir)` / `acquire("ibovespa", data_dir)` to run one getter. `data_dir` is optional in both calls. `acquire_ifix(data_dir)` and `acquire_ibovespa(data_dir)` remain available as convenience functions. `acquire_all` propagates an exception immediately and stops; incomplete reports are returned normally. Reports include saved, updated, unchanged and failed years. Importing modules or starting the application must not make network requests.

## B3 annual daily evolution

Install Python 3.9 or later. From the repository root, create the backend virtual environment and install its declared dependencies (the downloader currently uses only the Python standard library):

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Run all registered getters (IFIX and IBOVESPA):

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter
```

To run only one getter, select it before any subcommand:

```powershell
.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --getter ibovespa
```

Use `--getter ifix` to run only IFIX. The default all-getters command reports failures and continues to the next getter; it exits with status 1 if any getter fails or reports an incomplete run.

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

## Tests

From the repository root, run the module tests without contacting data providers:

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/src/internet_data_getter/tests
```
