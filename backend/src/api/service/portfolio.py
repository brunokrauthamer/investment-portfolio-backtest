"""Portfolio configuration validation and acknowledgement service."""

import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from backend.src.api.model.portfolio import PortfolioConfiguration
from backend.src.api.service.indexes import available_index_ids


class PortfolioConfigurationError(ValueError):
    """Raised when a submitted portfolio violates application rules."""


_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def _parse_date(value: str, field_name: str) -> date:
    if _DATE_PATTERN.fullmatch(value) is None:
        raise PortfolioConfigurationError(f"{field_name} must be a YYYY-MM-DD string")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise PortfolioConfigurationError(
            f"{field_name} must be a valid calendar date"
        ) from error


def _parse_percentage(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise PortfolioConfigurationError("percentage must be a JSON number")
    if isinstance(value, float) and not math.isfinite(value):
        raise PortfolioConfigurationError("percentage must be finite")
    try:
        percentage = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise PortfolioConfigurationError(
            "percentage must be a decimal number"
        ) from error
    if (
        not percentage.is_finite()
        or percentage < 0
        or percentage > 100
        or percentage.as_tuple().exponent < -2
    ):
        raise PortfolioConfigurationError(
            "percentage must be from 0 to 100 with at most two decimal places"
        )
    return percentage


def validate_portfolio_configuration(configuration: PortfolioConfiguration) -> None:
    """Apply portfolio rules that go beyond the HTTP request's wire shape."""
    initial_date = _parse_date(configuration.initial_date, "initial_date")
    end_date = _parse_date(configuration.end_date, "end_date")
    if initial_date > end_date:
        raise PortfolioConfigurationError("initial_date must be on or before end_date")

    allocations = configuration.allocations
    supported_indexes = available_index_ids()
    if not 1 <= len(allocations) <= len(supported_indexes):
        raise PortfolioConfigurationError(
            f"allocations must contain between 1 and {len(supported_indexes)} items"
        )

    allocated_indexes: set[str] = set()
    total_percentage = Decimal("0")
    for allocation in allocations:
        if allocation.index not in supported_indexes:
            raise PortfolioConfigurationError("allocation index is not supported")
        if allocation.index in allocated_indexes:
            raise PortfolioConfigurationError("allocation indexes must be unique")
        allocated_indexes.add(allocation.index)
        total_percentage += _parse_percentage(allocation.percentage)

    if total_percentage != Decimal("100"):
        raise PortfolioConfigurationError("allocation percentages must total exactly 100")


def accept_portfolio(configuration: PortfolioConfiguration) -> dict[str, str]:
    """Validate and acknowledge a configuration without storing or calculating it."""
    validate_portfolio_configuration(configuration)
    return {"status": "ok"}
