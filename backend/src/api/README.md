# API

FastAPI routes handle HTTP requests and responses. The ASGI application is exposed as `app` in `backend.src.api.main`; HTTP routes are grouped in `controller`. `service` and `model` are reserved for later use.

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
