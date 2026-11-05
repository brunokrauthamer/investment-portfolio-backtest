"""ASGI application entry point."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.src.api.controller.health import router as health_router
from backend.src.api.controller.portfolio import router as portfolio_router
from backend.src.api.service.portfolio import PortfolioConfigurationError

app = FastAPI()
app.include_router(health_router)
app.include_router(portfolio_router)


@app.exception_handler(PortfolioConfigurationError)
async def portfolio_configuration_error_handler(
    _request: Request, error: PortfolioConfigurationError
) -> JSONResponse:
    """Translate service validation errors into the API's 422 response."""
    return JSONResponse(status_code=422, content={"detail": str(error)})
