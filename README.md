# Investment portfolio backtesting

This project will help people explore how hypothetical investment portfolios would have performed historically. The planned dashboard uses React and TypeScript, with a Python/FastAPI modular-monolith backend and CSV data storage.

- `backend/`: planned API, application, domain, acquisition and storage boundaries.
- `frontend/`: planned dashboard.
- `data/`: reserved for acquired historical datasets.
- `docs/project-context.md`: confirmed decisions, data safety requirements and open questions.

The backend provides an explicit IFIX daily-evolution downloader. Set up the project virtual environment as described in the [download and recovery instructions](backend/src/acquisition/README.md), then run `.venv\Scripts\python -m backend.src.acquisition.ifix` from the repository root on Windows; it preserves B3's annual source files for 2011 through the current year under `data/ifix/source/`. No application startup or module import initiates a network request. Other data sources and financial conventions remain to be agreed before implementation. No synthetic market data is included.
