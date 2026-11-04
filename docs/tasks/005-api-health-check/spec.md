# API health check — specification s001

Status: proposed; awaiting human approval. The endpoint contract and implementation choices below are proposals for this request.

## Goal and scope

Create a small FastAPI entry point and organize `backend/src/api` into `controller`, `service`, and `model` directories. Add a health check in the controller. Service and model have no implementation yet; use an empty `.gitkeep` in each directory so Git retains the requested structure.

## Acceptance criteria

- **AC-001 — Structure:** `backend/src/api/controller` contains the health route; `service` and `model` exist with only empty `.gitkeep` placeholders. The existing API boundary remains separate from `internet_data_getter`.
- **AC-002 — Health endpoint:** The application registers `GET /health`, which responds with HTTP 200 and JSON `{"status":"ok"}`. The response indicates only that the application is serving requests; it does not claim that data sources or other dependencies are healthy. Other methods and paths use framework defaults.
- **AC-003 — Usable application:** A FastAPI application includes the health controller. Declare FastAPI, Uvicorn and the HTTP client needed by the route tests in `backend/requirements.txt`, and document setup, startup from the repository root, and the endpoint in the backend/API documentation.
- **AC-004 — Boundaries:** Importing or starting the application and serving this route does not initiate network requests, access market data, or run a getter. No financial behavior, frontend, health dependency probes, or market-data changes are introduced.

## Constraints and decisions

- The repository requires `backend/.venv` for backend Python commands and forbids network activity during imports or application startup.
- This is a process liveness route, with no authentication, persistence, custom error handling, readiness checks, or portfolio calculations in scope.
- The path, JSON body, empty-directory markers, and app entry point are proposed implementation details awaiting approval.
- The requested feature workflow includes test-first implementation and independent review and QA. Verification uses the backend virtual environment and avoids network access to external data providers.
