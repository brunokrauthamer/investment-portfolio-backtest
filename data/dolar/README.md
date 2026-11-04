# USD/BRL source data

The initial USD/BRL file was prepared from a CSV supplied by the user and attributed to [Investing.com USD/BRL historical data](https://br.investing.com/currencies/usd-brl-historical-data). The retrieval time and the source's current usage terms were not established. The manifest records the input and output hashes; it does not verify financial correctness or grant redistribution rights.

The active file is `source/USD_BRL Dados Históricos (1).csv`. It contains the source's `Data` and `Último` values in that order, with `Último` renamed `price`. Values and row order are retained as supplied. The CSV is comma-delimited, encoded as UTF-8 without a byte-order mark, and keeps the source date text (`DD.MM.YYYY`) and decimal-comma price text. Quotes in the CSV are field delimiters where needed; they do not change the stored value.

`manifest.json` describes this initial transformation and its hashes. Only files under `source/` are active observations. Keep manifests, pending records, backups and staging files outside that directory.

## Interrupted initial import

The initial import stages the CSV and manifest under `.staging/<transaction-id>/` and writes `.pending-import.json` before publishing either active file. The pending record lists the expected SHA-256 for both files and their staging and destination paths. It is removed only after both active files match those hashes. Because this was an initial creation with no previous USD/BRL source file, no historical backup was made.

To recover offline after an interruption, first confirm that no import process is running. Read `.pending-import.json` and compare the active and staged files with its expected hashes. If a destination is absent and its staged file has the expected hash, move that staged file to the listed destination; do not overwrite a file that already exists. If an active destination has a different hash, preserve the files and pending record for investigation. Once both active files match the recorded hashes, remove the transaction's remaining staging directory and pending record. To abandon an incomplete initial import, remove only active files whose hashes match the pending record, then remove that transaction's staging directory and pending record. No previous USD/BRL file can be restored because none existed before this import.

If `.staging/<transaction-id>/` remains without a pending record, confirm no import is running and check that no active files refer to it before removing the orphaned staging directory. Never treat staging or backup files as active data.

Future updates must be implemented as a separate task. Before replacing this active CSV or its manifest, preserve verified prior versions outside `source/`, under `data/backups/dolar/<version>/`, record the matching hashes and provenance, and document an offline restore procedure. No USD/BRL updater or restore command is included here.
