"""Portfolio configuration validation and acknowledgement service."""

import math
import re
import calendar
from datetime import date
from decimal import Decimal, InvalidOperation
from collections.abc import Mapping, Sequence

from backend.src.api.model.portfolio import PortfolioConfiguration
from backend.src.api.model.portfolio_data import DailyReturnObservation, load_daily_returns
from backend.src.api.service.indexes import available_index_ids


class PortfolioConfigurationError(ValueError):
    """Raised when a submitted portfolio violates application rules."""


class PortfolioCalculationError(ValueError):
    """Raised when daily returns do not define a usable portfolio result."""


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


_REBALANCING_MONTHS = {
    "3_months": 3,
    "6_months": 6,
    "1_year": 12,
    "2_years": 24,
    "3_years": 36,
}
_MILLISECONDS_PER_DAY = 86_400_000


def _anniversary(anchor: date, months_after_anchor: int) -> date:
    """Return an anchor anniversary, clamping its day to the target month's end."""
    month_index = anchor.year * 12 + anchor.month - 1 + months_after_anchor
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calculate_portfolio_series(
    observations: Sequence[DailyReturnObservation],
    allocations: Sequence[Mapping[str, object]],
    rebalancing: str,
) -> dict[str, list[dict[str, object]]]:
    """Calculate chart points from start-of-day weights and calendar resets."""
    if not observations:
        return {"series": [{"name": "Cumulative portfolio return", "data": []}]}

    target_weights = {
        str(allocation["index"]): float(_parse_percentage(allocation["percentage"])) / 100
        for allocation in allocations
    }
    weights = target_weights.copy()
    interval_months = _REBALANCING_MONTHS.get(rebalancing)
    anchor = observations[0].date
    months_after_anchor = interval_months
    growth = 1.0
    points: list[dict[str, object]] = []

    for observation in observations:
        daily_return = sum(
            weights[index] * observation.returns[index]
            for index in weights
        )
        growth_factor = 1 + daily_return
        if not math.isfinite(daily_return) or growth_factor <= 0 or not math.isfinite(growth_factor):
            raise PortfolioCalculationError("Portfolio returns do not define a valid result.")

        growth *= growth_factor
        if not math.isfinite(growth):
            raise PortfolioCalculationError("Portfolio returns do not define a valid result.")
        daily_percentage = daily_return * 100
        cumulative_percentage = (growth - 1) * 100
        if not math.isfinite(daily_percentage) or not math.isfinite(cumulative_percentage):
            raise PortfolioCalculationError("Portfolio returns do not define a valid result.")

        points.append({
            "x": (observation.date - date(1970, 1, 1)).days * _MILLISECONDS_PER_DAY,
            "y": cumulative_percentage,
            "date": observation.date.isoformat(),
            "daily_return_pct": daily_percentage,
            "cumulative_return_pct": cumulative_percentage,
        })

        weights = {
            index: weight * (1 + observation.returns[index]) / growth_factor
            for index, weight in weights.items()
        }
        if any(not math.isfinite(weight) for weight in weights.values()):
            raise PortfolioCalculationError("Portfolio returns do not define a valid result.")

        while (
            interval_months is not None
            and months_after_anchor is not None
            and _anniversary(anchor, months_after_anchor) <= observation.date
        ):
            weights = target_weights.copy()
            months_after_anchor += interval_months

    return {"series": [{"name": "Cumulative portfolio return", "data": points}]}


def calculate_portfolio(configuration: PortfolioConfiguration) -> dict[str, list[dict[str, object]]]:
    """Validate a request, load its available rows, and calculate the result."""
    validate_portfolio_configuration(configuration)
    initial_date = _parse_date(configuration.initial_date, "initial_date")
    end_date = _parse_date(configuration.end_date, "end_date")
    observations = load_daily_returns(initial_date, end_date)
    return calculate_portfolio_series(
        observations,
        [
            {"index": allocation.index, "percentage": allocation.percentage}
            for allocation in configuration.allocations
        ],
        configuration.rebalancing,
    )
