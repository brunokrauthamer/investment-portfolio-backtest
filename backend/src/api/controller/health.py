"""Health route for confirming that the API process is serving requests."""

from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return a simple liveness response."""
    return {"status": "ok"}
