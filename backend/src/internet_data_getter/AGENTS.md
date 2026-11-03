# Internet data getter

Keep each asset’s source-specific acquisition logic together in an asset directory (such as `ifix/`). This module owns downloading, validation, safe storage, provenance, backups and recovery for acquired source data.

The shared Python and command-line entry points serve all registered data getters. They must support explicitly running all getters or selecting a single getter, and must include future getters in the all-getters operation. Register each new getter and its command handler in the shared registry, so both entry points discover it. Keep source-specific logic, reporting and operations inside the relevant asset directory; the shared entry points coordinate registered getters. Imports and API startup must not initiate downloads. Share implementation across assets when a real common need is established, without requiring identical files for every source. Preserve project data safety and provenance requirements.

Keep tests for this module inside `backend/src/internet_data_getter/tests/`, including shared entry-point and asset-specific tests. Add tests for future getters there as well. Run them from the repository root with `.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/src/internet_data_getter/tests` on Windows.
