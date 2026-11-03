# Data acquisition

Acquisition runs only when an operator invokes a command. Importing modules or starting the application must not make network requests.

## IFIX daily evolution

Install Python 3.9 or later. From the repository root, create the project virtual environment and install its declared dependencies (the downloader currently uses only the Python standard library):

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Then run:

```powershell
.venv\Scripts\python -m backend.src.acquisition.ifix
```

The command fetches one B3 CSV for each year from 2011 through the current year using the same annual download endpoint used by the [B3 IFIX daily-evolution page](https://sistemaswebb3-listados.b3.com.br/indexStatisticsPage/daily-evolution/IFIX?language=pt-br). The page's semester selector changes the displayed half-year; the download itself contains the full year. Files are saved as `data/ifix/source/IFIX_<year>_Evolucao_Diaria.csv`. The page returns Base64 text and the command decodes it to the original CSV bytes, including its original character encoding; it does not parse or rewrite the observations. Validation checks the year header, all 12 month columns, the 31 day rows, summary rows, and at least one observation. Blank future months in the current-year file are accepted.

The command also writes `data/ifix/manifest.json` with each year's source URL, original B3 filename, retrieval time and SHA-256 digest. It reports saved, updated and unchanged files. HTTP, format, download and storage errors are listed by year, processing continues for other years, and any incomplete run exits with status 1.

### Safe reruns and recovery

An identical download does not change the active file or create a backup. When B3 changes an existing year's file, the previous bytes are copied and hash-verified under `data/backups/ifix/<year>/` before the active file is atomically replaced. The manifest lists backup paths and hashes under that year's `previous_versions`. A write-ahead manifest entry lets the next run recover the backup reference if a process stops after replacing the active file but before committing the manifest update. If recovery cannot match the active file to the recorded old or new hash, it stops and preserves the pending entry.

To restore an earlier version without contacting B3, use a backup path listed in that year's manifest:

```powershell
.venv\Scripts\python -m backend.src.acquisition.ifix --data-dir data restore --year 2011 --backup backups/ifix/2011/PASTE_BACKUP_PATH_FROM_MANIFEST.csv
```

Replace the example path with the exact manifest-relative backup path for that year. The restore verifies the listed backup's hash and CSV structure, backs up and records the currently active file, then atomically installs the selected version and updates provenance. It does not redownload the newest file. A later explicit download command may update the restored version again, after preserving it as another backup. Keep backups separate from `data/ifix/source/` so they are not mistaken for active source files.

An exclusive lock prevents concurrent runs. If a process is interrupted, `.acquisition.lock` may remain under `data/ifix/`. Confirm that no acquisition process is still running before deleting this stale lock and retrying. The command never removes a lock automatically.

The acquisition makes one paced HTTPS request per requested year with certificate verification enabled. It preserves files already saved if a later year fails. The page offers years dynamically through the current year; the current year may be partial. The stored file remains B3's monthly-by-day matrix and is not converted into a normalized daily series. B3 data is retained for the user's stated personal use; data-use and access terms belong to B3 and may change.
