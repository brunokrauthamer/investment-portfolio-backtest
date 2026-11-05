"""Request schemas for portfolio configuration endpoints."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Rebalancing = Literal["none", "3_months", "6_months", "1_year", "2_years", "3_years"]


class AllocationInput(BaseModel):
    """Wire schema for one index allocation."""

    model_config = ConfigDict(extra="forbid")

    index: str
    percentage: Any = Field(
        json_schema_extra={
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "multipleOf": 0.01,
        }
    )


class PortfolioConfiguration(BaseModel):
    """Wire schema for a portfolio configuration request."""

    model_config = ConfigDict(extra="forbid")

    initial_date: str = Field(json_schema_extra={"format": "date"})
    end_date: str = Field(json_schema_extra={"format": "date"})
    allocations: list[AllocationInput] = Field(
        json_schema_extra={"minItems": 1, "maxItems": 4}
    )
    rebalancing: Rebalancing
