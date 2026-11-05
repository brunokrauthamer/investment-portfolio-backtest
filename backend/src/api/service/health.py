"""Health service for API process liveness."""


def health_check() -> dict[str, str]:
    """Return the API process liveness status."""
    return {"status": "ok"}
