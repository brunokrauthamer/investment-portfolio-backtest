"""Portfolio setup endpoints; they validate and acknowledge configuration only."""

import json
import math
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DuplicateJsonMemberError(ValueError):
    """Raised when a JSON object contains the same member name more than once."""


def _unique_json_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    members: dict[str, object] = {}
    for key, value in pairs:
        if key in members:
            raise DuplicateJsonMemberError(f"Repeated JSON member: {key}")
        members[key] = value
    return members


def _reject_nonstandard_json_number(token: str) -> None:
    raise ValueError(f"Nonfinite JSON number: {token}")


def _parse_decimal_json_number(token: str) -> Decimal:
    try:
        number = Decimal(token)
    except InvalidOperation as error:
        raise ValueError("Invalid decimal JSON number") from error
    if (
        not number.is_finite()
        or number < 0
        or number > 100
        or number.as_tuple().exponent < -2
    ):
        raise ValueError("Percentage JSON numbers must be from 0 to 100 with at most two decimal places")
    return number


def _parse_integer_json_number(token: str) -> int:
    number = int(token)
    if number < 0 or number > 100:
        raise ValueError("Percentage JSON integers must be from 0 to 100")
    return number


class ExactJsonRoute(APIRoute):
    """Decode JSON decimals before FastAPI validates the typed request body."""

    def get_route_handler(self):
        original_handler = super().get_route_handler()

        async def decode_exact_json(request: Request):
            media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            raw_body = await request.body()
            if raw_body:
                is_json_media_type = (
                    not media_type
                    or media_type == "application/json"
                    or media_type.endswith("+json")
                )
                if not is_json_media_type:
                    raise HTTPException(
                        status_code=422,
                        detail="The request body must use a JSON media type.",
                    )
                try:
                    # Starlette caches Request.json() in _json; seed it so FastAPI's typed
                    # body validation receives exact decimals and duplicate keys are visible.
                    request._json = json.loads(
                        raw_body,
                        parse_float=_parse_decimal_json_number,
                        parse_int=_parse_integer_json_number,
                        parse_constant=_reject_nonstandard_json_number,
                        object_pairs_hook=_unique_json_members,
                    )
                except (UnicodeDecodeError, ValueError, RecursionError) as error:
                    raise HTTPException(
                        status_code=422,
                        detail="The JSON body contains invalid or repeated values.",
                    ) from error
            return await original_handler(request)

        return decode_exact_json


router = APIRouter(prefix="/api", route_class=ExactJsonRoute)

_INDEXES = (
    {"id": "ibovespa", "name": "IBOVESPA"},
    {"id": "ifix", "name": "IFIX"},
    {"id": "selic", "name": "Selic"},
    {"id": "sp500", "name": "S&P 500"},
)
IndexId = Literal["ibovespa", "ifix", "selic", "sp500"]
Rebalancing = Literal["none", "3_months", "6_months", "1_year", "2_years", "3_years"]


class AllocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: IndexId
    percentage: Decimal = Field(ge=Decimal("0"), le=Decimal("100"), max_digits=5, decimal_places=2)

    @field_validator("percentage", mode="before")
    @classmethod
    def require_json_number(cls, value: object) -> Decimal:
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("percentage must be a JSON number")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("percentage must be finite")
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise ValueError("percentage must be a decimal number") from error


class PortfolioConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initial_date: date
    end_date: date
    allocations: list[AllocationInput] = Field(min_length=1, max_length=4)
    rebalancing: Rebalancing

    @field_validator("initial_date", "end_date", mode="before")
    @classmethod
    def require_iso_calendar_date(cls, value: object) -> date:
        if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
            raise ValueError("date must be a YYYY-MM-DD string")
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("date must be a valid calendar date") from error

    @model_validator(mode="after")
    def validate_configuration(self) -> "PortfolioConfiguration":
        if self.initial_date > self.end_date:
            raise ValueError("initial_date must be on or before end_date")
        index_ids = [allocation.index for allocation in self.allocations]
        if len(index_ids) != len(set(index_ids)):
            raise ValueError("allocation indexes must be unique")
        if sum((allocation.percentage for allocation in self.allocations), Decimal("0")) != Decimal("100"):
            raise ValueError("allocation percentages must total exactly 100")
        return self


@router.get("/indexes")
def list_indexes() -> list[dict[str, str]]:
    """Return the fixed set of index identifiers available to the form."""
    return list(_INDEXES)


@router.post("/portfolio")
def accept_portfolio(_configuration: PortfolioConfiguration) -> dict[str, str]:
    """Acknowledge a valid configuration without storing or calculating it."""
    return {"status": "ok"}
