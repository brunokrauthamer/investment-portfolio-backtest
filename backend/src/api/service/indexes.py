"""Service for the index choices exposed by the portfolio form."""

_INDEXES = (
    {"id": "ibovespa", "name": "IBOVESPA"},
    {"id": "ifix", "name": "IFIX"},
    {"id": "selic", "name": "Selic"},
    {"id": "sp500", "name": "S&P 500"},
)


def list_indexes() -> list[dict[str, str]]:
    """Return a fresh list of the index identifiers available to the form."""
    return [dict(index) for index in _INDEXES]


def available_index_ids() -> frozenset[str]:
    """Return the supported index identifiers for portfolio validation."""
    return frozenset(index["id"] for index in _INDEXES)
