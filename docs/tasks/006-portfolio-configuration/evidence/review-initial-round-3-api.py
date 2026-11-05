"""Independent raw-body checks for the third portfolio review."""

import json
import sys
import traceback

import fastapi
from fastapi.testclient import TestClient

from backend.src.api.main import app


path = "/api/portfolio"
prefix = (
    '{"initial_date":"2020-01-01","end_date":"2024-12-31",'
    '"allocations":[{"index":"ifix","percentage":'
)
suffix = '}],"rebalancing":"none"}'
json_headers = {"content-type": "application/json"}
body = prefix + "100" + suffix
invalid_tokens = (
    "99.9999999999999999",
    "100.0000000000000001",
    "100.000",
    "1e309",
    "NaN",
    "Infinity",
    '50,"percentage":100',
)

print(f"Python {sys.version.split()[0]}, FastAPI {fastapi.__version__}")
with TestClient(app, raise_server_exceptions=False) as client:
    for media_type in (
        None, "", "application/json", "APPLICATION/JSON; charset=utf-8",
        "application/vnd.portfolio+json",
    ):
        headers = {} if media_type is None else {"content-type": media_type}
        valid = client.post(path, content=body, headers=headers)
        assert (valid.status_code, valid.json()) == (200, {"status": "ok"})
        for token in invalid_tokens:
            response = client.post(path, content=prefix + token + suffix, headers=headers)
            assert response.status_code == 422 and response.json()["detail"]
        print(f"{media_type!r}: valid -> {valid.status_code}; {len(invalid_tokens)} invalid cases -> 422")

    unsupported = client.post(path, content=body, headers={"content-type": "text/plain"})
    assert unsupported.status_code == 422 and unsupported.json()["detail"]
    print("text/plain with valid JSON -> 422")

    for depth in (950, 1500):
        nested = '{"unexpected":' + "[" * depth + "0" + "]" * depth + "}"
        response = client.post(path, content=nested, headers=json_headers)
        assert response.status_code == 422 and response.json()["detail"]
        print(f"Invalid JSON shape with {depth} array levels -> 422")

    invalid_unicode = body.replace('"rebalancing":"none"', r'"rebalancing":"\ud800"')
    assert json.loads(invalid_unicode)["rebalancing"] == "\ud800"
    response = client.post(path, content=invalid_unicode, headers=json_headers)
    print(f"Invalid strategy containing escaped lone surrogate -> {response.status_code} {response.text}")
    assert response.status_code == 500, "Update this reproduction if the finding is resolved"

with TestClient(app) as client:
    try:
        client.post(path, content=invalid_unicode, headers=json_headers)
    except UnicodeEncodeError as error:
        frames = traceback.extract_tb(error.__traceback__)
        print("Error response stack:")
        for frame in frames[-6:]:
            print(f"  {frame.filename.replace(chr(92), '/').split('/')[-1]}:{frame.lineno} in {frame.name}")
        print(f"  {type(error).__name__}: {error.reason}")
    else:
        raise AssertionError("Expected response serialization to raise UnicodeEncodeError")
