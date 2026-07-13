"""Real-time price streaming operations for the Tradowix client."""
from __future__ import annotations

import logging

from pytradowix._base import _ClientBase

logger = logging.getLogger(__name__)


class RealtimeMixin(_ClientBase):
    """Real-time operations (price streaming subscriptions) for TradoWix."""

    async def subscribe_ticks(
        self,
        symbol: str,
        lookback_minutes: int = 200,
        timeframe: int = 60,
        chart_type: str = "candle"
    ) -> None:
        """Subscribe to real-time price tick feed for a symbol.
        
        Args:
            symbol: Asset symbol (e.g. "USDJPY-OTC")
            lookback_minutes: Lookback history to pre-fetch (default: 200)
            timeframe: Candle timeframe in seconds (default: 60)
            chart_type: Chart rendering type (default: "candle")
        """
        msg = {
            "type": "subscribeTicks",
            "symbol": symbol,
            "lookbackMinutes": lookback_minutes,
            "timeframe": timeframe,
            "chartType": chart_type
        }
        logger.info(f"Subscribing to tick updates for {symbol}")
        self._subscribed_symbols.add(symbol)
        await self._send_ws(msg)

    async def unsubscribe_ticks(self, symbol: str) -> None:
        """Unsubscribe from real-time price tick feed for a symbol."""
        msg = {
            "type": "unsubscribeTicks",
            "symbol": symbol
        }
        logger.info(f"Unsubscribing from tick updates for {symbol}")
        self._subscribed_symbols.discard(symbol)
        await self._send_ws(msg)

