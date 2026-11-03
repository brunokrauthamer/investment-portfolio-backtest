# Data

This directory holds acquired historical datasets. The IFIX and IBOVESPA downloaders store original B3 annual files in `ifix/source/` and `ibovespa/source/`, with provenance in each asset's `manifest.json`. Updates place recoverable prior versions under `backups/ifix/<year>/` and `backups/ibovespa/<year>/`. Do not use backup files as active inputs. See [acquisition instructions](../backend/src/internet_data_getter/README.md) for download and restore steps.
