"""Check API import and ASGI startup/request with external access blocked."""

from __future__ import annotations

import builtins
import io
import json
from pathlib import Path
import socket
import sys


ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = (ROOT / "data").resolve()
sys.path.insert(0, str(ROOT))
external_network_attempts = []
data_file_attempts = []
allowed_hosts = {"", "localhost", "127.0.0.1", "::1"}

original_connect = socket.socket.connect
original_create_connection = socket.create_connection
original_getaddrinfo = socket.getaddrinfo
original_builtin_open = builtins.open
original_io_open = io.open


def is_external_host(host):
    return isinstance(host, str) and host.lower().split("%", 1)[0] not in allowed_hosts


def guarded_connect(sock, address):
    host = address[0] if isinstance(address, tuple) and address else None
    if is_external_host(host):
        external_network_attempts.append(("connect", host))
        raise AssertionError(f"External socket connection blocked: {host}")
    return original_connect(sock, address)


def guarded_create_connection(address, *args, **kwargs):
    host = address[0] if isinstance(address, tuple) and address else None
    if is_external_host(host):
        external_network_attempts.append(("create_connection", host))
        raise AssertionError(f"External socket connection blocked: {host}")
    return original_create_connection(address, *args, **kwargs)


def guarded_getaddrinfo(host, *args, **kwargs):
    if is_external_host(host):
        external_network_attempts.append(("getaddrinfo", host))
        raise AssertionError(f"External DNS lookup blocked: {host}")
    return original_getaddrinfo(host, *args, **kwargs)


def is_market_data_path(file):
    if isinstance(file, int):
        return False
    try:
        path = Path(file).resolve()
        return path == DATA_DIR or DATA_DIR in path.parents
    except (OSError, TypeError, ValueError):
        return False


def guarded_open(file, *args, **kwargs):
    if is_market_data_path(file):
        data_file_attempts.append(str(file))
        raise AssertionError(f"Market data access blocked: {file}")
    return original_builtin_open(file, *args, **kwargs)


def guarded_io_open(file, *args, **kwargs):
    if is_market_data_path(file):
        data_file_attempts.append(str(file))
        raise AssertionError(f"Market data access blocked: {file}")
    return original_io_open(file, *args, **kwargs)


socket.socket.connect = guarded_connect
socket.create_connection = guarded_create_connection
socket.getaddrinfo = guarded_getaddrinfo
builtins.open = guarded_open
io.open = guarded_io_open

from fastapi.testclient import TestClient

from backend.src.api.main import app

with TestClient(app) as client:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

assert not any(name.startswith("backend.src.internet_data_getter") for name in sys.modules)
assert not external_network_attempts, external_network_attempts
assert not data_file_attempts, data_file_attempts
print(json.dumps({
    "api_imported": "backend.src.api.main",
    "asgi_startup_completed": True,
    "guarded_get_health": {"status": response.status_code, "json": response.json()},
    "getter_modules_loaded": False,
    "external_network_attempts": external_network_attempts,
    "market_data_file_attempts": data_file_attempts,
}, indent=2))
