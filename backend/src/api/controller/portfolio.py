"""HTTP routes for portfolio setup."""

from fastapi import APIRouter

from backend.src.api.model.portfolio import PortfolioConfiguration
from backend.src.api.service.indexes import list_indexes as get_indexes
from backend.src.api.service.portfolio import accept_portfolio as submit_portfolio
from backend.src.api.transport.exact_json import ExactJsonRoute


router = APIRouter(prefix="/api", route_class=ExactJsonRoute)


@router.get("/indexes")
def list_indexes() -> list[dict[str, str]]:
    """Connect the index-listing endpoint to its service."""
    return get_indexes()


@router.post("/portfolio")
def accept_portfolio(configuration: PortfolioConfiguration) -> dict[str, str]:
    """Connect the portfolio endpoint to its service."""
    return submit_portfolio(configuration)
