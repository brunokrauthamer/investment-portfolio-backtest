# Investment portfolio backtesting

This project will help people explore how hypothetical investment portfolios would have performed historically. The planned dashboard uses React and TypeScript, with a Python/FastAPI modular-monolith backend and CSV data storage.

- `backend/`: backend modules, local Python environment and dependency manifest.
- `frontend/`: planned dashboard.
- `data/`: acquired historical datasets.
- `docs/project-context.md`: confirmed decisions, data safety requirements and open questions.

The backend provides explicit IFIX and Selic acquisition commands. Set up the backend virtual environment as described in the [acquisition and recovery instructions](backend/src/internet_data_getter/README.md), then run `.\backend\.venv\Scripts\python.exe -m backend.src.internet_data_getter --getter selic` from the repository root on Windows to scrape BCB SGS 11 into `data/selic/source/selic_sgs_11.csv`. No application startup or module import initiates a network request. Financial calculations and data alignment conventions remain separate from acquisition. No synthetic market data is included.
