"""Exercise the documented Uvicorn entry point over loopback HTTP."""

from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


root = Path(__file__).resolve().parents[4]
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]

command = [
    sys.executable,
    "-m",
    "uvicorn",
    "backend.src.api.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    str(port),
    "--no-access-log",
]
creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
process = subprocess.Popen(
    command,
    cwd=root,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    creationflags=creationflags,
)
url = f"http://127.0.0.1:{port}"
results = {}

try:
    response = None
    last_error = None
    for _ in range(100):
        if process.poll() is not None:
            break
        try:
            response = urlopen(f"{url}/health", timeout=1)
            break
        except URLError as error:
            last_error = error
            time.sleep(0.1)
    if process.poll() is not None:
        raise RuntimeError("Uvicorn exited before becoming ready.")
    if response is None:
        raise RuntimeError(f"Uvicorn did not become ready: {last_error}")

    body = response.read()
    results["GET /health"] = {
        "status": response.status,
        "content_type": response.headers.get_content_type(),
        "json": json.loads(body),
    }

    try:
        urlopen(Request(f"{url}/health", method="POST"), timeout=3)
    except HTTPError as error:
        results["POST /health"] = {"status": error.code}

    try:
        urlopen(f"{url}/missing", timeout=3)
    except HTTPError as error:
        results["GET /missing"] = {"status": error.code}
finally:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    server_output = process.stdout.read() if process.stdout else ""

if results.get("GET /health") != {
    "status": 200,
    "content_type": "application/json",
    "json": {"status": "ok"},
}:
    raise AssertionError(f"Unexpected health response: {results.get('GET /health')!r}")
if results.get("POST /health", {}).get("status") != 405:
    raise AssertionError(f"Unexpected unsupported-method response: {results!r}")
if results.get("GET /missing", {}).get("status") != 404:
    raise AssertionError(f"Unexpected unknown-path response: {results!r}")

print(json.dumps({"command": command, "results": results, "server_output": server_output}, indent=2))
