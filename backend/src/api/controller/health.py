"""Health route for confirming that the API process is serving requests."""

from fastapi import APIRouter

from backend.src.api.service.health import health_check as get_health_status


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Connect the health endpoint to its service."""
    return get_health_status()
