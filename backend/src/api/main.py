"""ASGI application entry point."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from backend.src.api.controller.health import router as health_router
from backend.src.api.controller.portfolio import router as portfolio_router
from backend.src.api.model.portfolio_data import PortfolioDataError
from backend.src.api.service.portfolio import PortfolioCalculationError, PortfolioConfigurationError

app = FastAPI()
app.include_router(health_router)
app.include_router(portfolio_router)


@app.exception_handler(PortfolioConfigurationError)
async def portfolio_configuration_error_handler(
    _request: Request, error: PortfolioConfigurationError
) -> JSONResponse:
    """Translate service validation errors into the API's 422 response."""
    return JSONResponse(status_code=422, content={"detail": str(error)})


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _request: Request, _error: RequestValidationError
) -> JSONResponse:
    """Return a safe validation response even for unencodable input strings."""
    return JSONResponse(status_code=422, content={"detail": "The request contains invalid or missing fields."})


@app.exception_handler(PortfolioDataError)
@app.exception_handler(PortfolioCalculationError)
async def portfolio_data_error_handler(
    _request: Request, _error: ValueError
) -> JSONResponse:
    """Avoid false acknowledgements and never expose local CSV paths."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Historical portfolio results are unavailable for this request."},
    )
