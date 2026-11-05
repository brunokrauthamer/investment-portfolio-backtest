# API

FastAPI routes handle HTTP requests and responses. The ASGI application is exposed as `app` in `backend.src.api.main`; HTTP routes are grouped in `controller`. Controllers delegate behavior to `service`, while request and response schemas live in `model`. HTTP decoding adapters that are not endpoint behavior live in `transport`.

From the repository root, create and prepare the backend environment once:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Start the API from the repository root on Windows:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn backend.src.api.main:app --reload
```

`GET http://127.0.0.1:8000/health` returns HTTP 200 with `{"status":"ok"}` while the API process is serving requests. This is a liveness response; it does not check data providers or market data. Importing and starting the API do not initiate data acquisition.

`POST http://127.0.0.1:8000/api/portfolio` returns a chart-ready `series` computed from `data/normalized/daily_returns_reais.csv`. The model layer uses pandas to validate and filter the CSV; the service calculates daily portfolio returns, weight drift, compounding and calendar rebalancing; the controller handles the HTTP contract. The response's ApexCharts series can be passed to the chart as received. CSV and calculation failures return HTTP 503, and invalid request bodies return HTTP 422.
