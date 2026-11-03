# Backend modules

Organize backend code by responsibility under `backend/src/`. `internet_data_getter` owns acquisition from external sources through safe preservation of source files; `api` is a separate sibling module. Do not contact the network on import or application startup.

Use `backend/.venv` for backend Python commands and maintain `backend/requirements.txt` when dependencies change. The environment is local and must not be committed.
