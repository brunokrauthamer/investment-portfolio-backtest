"""Explicit entry points for source data acquisition."""
from __future__ import annotations

from typing import NamedTuple, Callable, Any
from .ifix import acquire_ifix
from .ifix import cli as ifix_cli
from .ibovespa import acquire_ibovespa
from .ibovespa import cli as ibovespa_cli
from .selic import acquire_selic
from .selic import cli as selic_cli
from .sp500 import acquire_sp500
from .sp500 import cli as sp500_cli


class _Getter(NamedTuple):
    run: Callable[..., Any]
    cli: Any

# Register each supported getter here so acquire_all includes it.
_GETTERS = {
    "ifix": _Getter(acquire_ifix, ifix_cli),
    "ibovespa": _Getter(acquire_ibovespa, ibovespa_cli),
    "selic": _Getter(acquire_selic, selic_cli),
    "sp500": _Getter(acquire_sp500, sp500_cli),
}


def available_getters():
    """Return the registered getter names."""
    return tuple(_GETTERS)


def acquire(name, data_dir=None):
    """Run one named getter; reject unknown names before accessing the network."""
    try:
        getter = _GETTERS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown data getter: {name}") from exc
    return getter.run(data_dir)


def acquire_all(data_dir=None):
    """Run all registered getters and return their results keyed by name.

    An exception stops the run and propagates to the caller.
    """
    return {name: acquire(name, data_dir) for name in _GETTERS}
