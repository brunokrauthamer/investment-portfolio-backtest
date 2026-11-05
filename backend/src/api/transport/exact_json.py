"""HTTP request decoding that preserves exact JSON numbers."""

import json
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, Request
from fastapi.routing import APIRoute


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
        return Decimal(token)
    except InvalidOperation as error:
        raise ValueError("Invalid decimal JSON number") from error


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
                        parse_constant=_reject_nonstandard_json_number,
                        object_pairs_hook=_unique_json_members,
                    )
                except (UnicodeDecodeError, ValueError, InvalidOperation, RecursionError) as error:
                    raise HTTPException(
                        status_code=422,
                        detail="The JSON body contains invalid or repeated values.",
                    ) from error
            return await original_handler(request)

        return decode_exact_json
