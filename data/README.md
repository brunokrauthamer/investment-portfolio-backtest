# Data

The Yahoo Finance S&P 500 getter writes its adjusted-close observations to `sp500/source/sp500_yahoo.csv` and provenance to `sp500/manifest.json`. Replaced versions are kept as verified CSV/manifest pairs under `backups/sp500/` and are restored only through the manifest-listed `restore-sp500` command.

This directory holds acquired historical datasets. The IFIX and IBOVESPA downloaders store original B3 annual files in `ifix/source/` and `ibovespa/source/`, with provenance in each asset's `manifest.json`. The Selic getter stores BCB SGS series 11 in a generated UTF-8 CSV at `selic/source/selic_sgs_11.csv`, with provenance in `selic/manifest.json`. Verified prior versions are kept under `backups/`; do not use backup files as active inputs. See [acquisition instructions](../backend/src/internet_data_getter/README.md) for download and offline restore steps.
