from __future__ import annotations
from typing import Optional, Tuple
from pytradowix.types import Candle

class CandleAggregator:
    """Aggregates a stream of price ticks into OHLC candles for a specific timeframe."""

    def __init__(self, period_seconds: int = 60) -> None:
        self.period_seconds = period_seconds
        self.current_candle: Optional[Candle] = None

    def add_tick(self, price: float, timestamp: float) -> Tuple[Candle, bool]:
        """Add a price tick and return the (candle, is_closed) state.

        Args:
            price: Current quote price.
            timestamp: Quote timestamp in seconds.

        Returns:
            Tuple[Candle, bool]: The current/closed candle and whether it closed.
        """
        candle_time = int(timestamp // self.period_seconds) * self.period_seconds

        if self.current_candle is None:
            self.current_candle = Candle(
                time=candle_time,
                open=price,
                high=price,
                low=price,
                close=price,
            )
            return self.current_candle, False

        if candle_time > self.current_candle.time:
            # Current candle is closed, start a new one
            closed_candle = self.current_candle
            self.current_candle = Candle(
                time=candle_time,
                open=price,
                high=price,
                low=price,
                close=price,
            )
            return closed_candle, True
        else:
            # Update values of the current active candle
            high = max(self.current_candle.high, price)
            low = min(self.current_candle.low, price)
            self.current_candle = Candle(
                time=self.current_candle.time,
                open=self.current_candle.open,
                high=high,
                low=low,
                close=price,
            )
            return self.current_candle, False
