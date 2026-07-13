"""Historical candle data retrieval for the Tradowix client."""
from __future__ import annotations

import asyncio
import time
import logging
from typing import Optional, List

from pytradowix._base import _ClientBase
from pytradowix.exceptions import TradowixTimeoutError, TradowixException
from pytradowix.types import Candle

logger = logging.getLogger(__name__)


class HistoryMixin(_ClientBase):
    """Historical candle data queries via backward pagination."""

    async def get_candles(
        self,
        symbol: str,
        end_from_time: float,
        minutes: int,
        timeframe: int,
        timeout: float = 10.0,
    ) -> List[Candle]:
        """Request a single batch of historical candles.

        Sends a ``requestOlderTicks`` WebSocket message and waits for the
        ``candleHistory`` response.

        Args:
            symbol: Asset symbol (e.g. ``"USDJPY-OTC"``).
            end_from_time: Boundary unix timestamp in *seconds*. Candles
                older than this timestamp will be returned.
            minutes: Number of minutes of history to request (e.g. ``400``).
            timeframe: Candle period in seconds (e.g. ``60`` for 1-minute bars).
            timeout: Per-request timeout in seconds (default: ``10.0``).

        Returns:
            list[Candle]: Sorted list of typed candle objects.

        Raises:
            TradowixException: If not connected.
            TradowixTimeoutError: If the server does not respond in time.
        """
        if not self._ws or self._ws.state.name != "OPEN":
            raise TradowixException("WebSocket is not connected")

        req_id = f"history-{int(time.time() * 1000)}"
        slot = self._slots.candle_history(req_id)
        slot.clear()

        msg = {
            "type": "requestOlderTicks",
            "symbol": symbol,
            "olderThan": int(end_from_time * 1000),  # broker expects ms
            "minutes": minutes,
            "timeframe": timeframe,
            "requestId": req_id,
        }

        logger.debug(f"Sending requestOlderTicks: {msg}")
        try:
            await self._send_ws(msg)
            res = await slot.wait(timeout=timeout)
            raw_candles = res.get("candles", [])
            return [Candle.from_array(c) for c in raw_candles if len(c) >= 5]
        except asyncio.TimeoutError as e:
            raise TradowixTimeoutError(
                f"History request timed out for {req_id}"
            ) from e
        finally:
            self._slots.release_candle_history(req_id)

    async def get_historical_candles(
        self,
        symbol: str,
        amount_of_seconds: int,
        period: int,
        end_from_time: Optional[float] = None,
        timeout: float = 10.0,
    ) -> List[Candle]:
        """Fetch historical candles by paginating backward through broker history.

        Repeatedly calls ``get_candles()`` with progressively older ``end_from_time``
        boundaries until ``amount_of_seconds`` of history is covered or the broker
        returns no more data.

        Args:
            symbol: Asset symbol (e.g. ``"USDJPY-OTC"``).
            amount_of_seconds: Total seconds of history to retrieve.
                Examples: ``3600`` (1 h), ``604800`` (1 week), ``2592000`` (30 days).
            period: Candle period in seconds (e.g. ``60`` for 1-minute bars).
            end_from_time: End boundary unix timestamp in *seconds*.
                Defaults to ``time.time()`` (current time).
            timeout: Per-chunk request timeout in seconds (default: ``10.0``).

        Returns:
            list[Candle]: Chronologically sorted, deduplicated list of typed candles.
        """
        if end_from_time is None:
            end_from_time = time.time()

        target_start_time = end_from_time - amount_of_seconds
        all_candles: dict[int, Candle] = {}

        was_subscribed = symbol in self._subscribed_symbols
        chart_slot = self._slots.chart_load(symbol)
        chart_slot.clear()

        initial_data = None
        if not was_subscribed:
            try:
                # Estimate required lookback minutes to request in initial subscription
                lookback_minutes = max(200, int(amount_of_seconds / 60) + 10)
                await self.subscribe_ticks(
                    symbol=symbol,
                    lookback_minutes=lookback_minutes,
                    timeframe=period,
                )
                logger.info("Waiting for initial chart load candle history...")
                initial_data = await chart_slot.wait(timeout=timeout)
            except Exception as e:
                logger.warning(f"Failed to load initial chart history for {symbol}: {e}")
            finally:
                self._slots.release_chart_load(symbol)
        else:
            if chart_slot.is_set():
                initial_data = chart_slot._value

        if initial_data:
            raw_candles = initial_data.get("candles", [])
            for c in raw_candles:
                if len(c) >= 5:
                    candle = Candle.from_array(c)
                    if candle.time >= target_start_time and candle.time <= end_from_time:
                        all_candles[candle.time] = candle

        # Determine starting point for backward pagination
        if all_candles:
            current_end_time = sorted(all_candles.keys())[0]
        else:
            current_end_time = int(end_from_time)

        minutes_chunk = 400  # safe batch size per request
        chunk_seconds = minutes_chunk * 60
        total_chunks = max(1, (amount_of_seconds + chunk_seconds - 1) // chunk_seconds)
        chunk_index = 0

        logger.info(
            f"Fetching historical candles for {symbol} "
            f"from {current_end_time:.0f} back to {target_start_time:.0f}"
        )

        while current_end_time > target_start_time:
            chunk_index += 1
            logger.info(f"Fetching chunk {chunk_index}/{total_chunks}...")
            try:
                batch = await self.get_candles(
                    symbol=symbol,
                    end_from_time=current_end_time,
                    minutes=minutes_chunk,
                    timeframe=period,
                    timeout=timeout,
                )
            except Exception as e:
                logger.error(f"Error fetching candle batch ending at {current_end_time}: {e}")
                break

            if not batch:
                logger.info("No more candles returned by broker. Stopping pagination.")
                break

            batch_times: list[int] = []
            for candle in batch:
                if candle.time >= target_start_time and candle.time <= end_from_time:
                    all_candles[candle.time] = candle
                    batch_times.append(candle.time)

            if not batch_times:
                logger.info("Batch empty within time boundary. Stopping pagination.")
                break

            batch_times.sort()
            new_oldest_time = batch_times[0]

            if new_oldest_time >= current_end_time:
                current_end_time -= chunk_seconds
            else:
                current_end_time = new_oldest_time

            await asyncio.sleep(0.1)

        # Cleanup: Unsubscribe if we subscribed temporarily
        if not was_subscribed:
            try:
                await self.unsubscribe_ticks(symbol)
            except Exception as e:
                logger.warning(f"Failed to unsubscribe from {symbol} after history fetch: {e}")

        return sorted(all_candles.values(), key=lambda c: c.time)
