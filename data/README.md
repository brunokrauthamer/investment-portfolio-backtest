# Data

This directory holds acquired historical datasets. The IFIX downloader stores original B3 annual files in `ifix/source/` and its metadata in `ifix/manifest.json`; updates place recoverable prior versions under `backups/ifix/<year>/`. Do not use backup files as active inputs. See [acquisition instructions](../backend/src/internet_data_getter/README.md) for download and restore steps.
