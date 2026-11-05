"""HTTP routes for portfolio setup."""

from fastapi import APIRouter

from backend.src.api.model.portfolio import PortfolioConfiguration, PortfolioResponse
from backend.src.api.service.indexes import list_indexes as get_indexes
from backend.src.api.service.portfolio import calculate_portfolio as run_portfolio
from backend.src.api.transport.exact_json import ExactJsonRoute


router = APIRouter(prefix="/api", route_class=ExactJsonRoute)


@router.get("/indexes")
def list_indexes() -> list[dict[str, str]]:
    """Connect the index-listing endpoint to its service."""
    return get_indexes()


@router.post("/portfolio", response_model=PortfolioResponse)
def calculate_portfolio(configuration: PortfolioConfiguration) -> PortfolioResponse:
    """Run the configured portfolio and return its chart-ready series."""
    return run_portfolio(configuration)
