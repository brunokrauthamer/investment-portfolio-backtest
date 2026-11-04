"""Generate daily asset returns expressed in Brazilian reais."""

from .service import NormalizationError, generate_daily_returns_reais

__all__ = ["NormalizationError", "generate_daily_returns_reais"]
