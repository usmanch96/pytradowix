"""pytradowix — Unofficial Python client for the TradoWix trading platform."""
import logging

from pytradowix.client import Tradowix
from pytradowix.exceptions import TradowixException, TradowixAuthError, TradowixTimeoutError
from pytradowix.types import (
    AssetInfo,
    Balance,
    Candle,
    ProfileInfo,
    Quote,
    ReconnectPolicy,
    TradeDirection,
    TradeResult,
    TradeStatus,
)


def _prepare_logging() -> None:
    """Install a NullHandler so the library never emits noise by default."""
    logging.getLogger(__name__).addHandler(logging.NullHandler())
    logging.getLogger("websockets").addHandler(logging.NullHandler())


_prepare_logging()


__all__ = [
    "Tradowix",
    # Exceptions
    "TradowixException",
    "TradowixAuthError",
    "TradowixTimeoutError",
    # Types
    "AssetInfo",
    "Balance",
    "Candle",
    "ProfileInfo",
    "Quote",
    "ReconnectPolicy",
    "TradeDirection",
    "TradeResult",
    "TradeStatus",
]
