# Backend modules

Organize backend code by responsibility under `backend/src/`. `internet_data_getter` owns acquisition from external sources through safe preservation of source files; `api` is a separate sibling module. Do not contact the network on import or application startup.
