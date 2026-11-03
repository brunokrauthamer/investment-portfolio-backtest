# Storage

CSV storage adapters follow the backup and atomic-write requirements in [project context](../../../docs/project-context.md).

`ifix.py` stores the annual IFIX source bytes and an atomic provenance manifest under the configured data directory. It validates the complete nested manifest before changing active data, writes a pending transaction before an active replacement, verifies backups by SHA-256, and reconciles interrupted replacements on the next operation. Restore only accepts a matching, manifest-listed backup; it backs up the displaced file and atomically installs the selected bytes without network access.
