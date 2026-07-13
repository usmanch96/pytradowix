"""Trading operations for the Tradowix client."""
from __future__ import annotations

import asyncio
import time
import uuid
import logging
from typing import Optional, Any, Literal, List

from websockets.protocol import State as WsState

from pytradowix._base import _ClientBase
from pytradowix.exceptions import TradowixTimeoutError, TradowixException
from pytradowix.types import TradeResult, TradeDirection

logger = logging.getLogger(__name__)


class TradingMixin(_ClientBase):
    """Binary options trade placement and result checking."""

    async def buy(
        self,
        amount: float,
        symbol: str,
        direction: TradeDirection,
        duration: int = 1,
        is_demo: Optional[bool] = None,
        expiration_mode: Literal["turbo", "blitz"] = "turbo",
    ) -> dict[str, Any]:
        """Place a call (Higher) trade.

        Args:
            amount: Investment amount in account currency (e.g. ``1.0``).
            symbol: Asset symbol (e.g. ``"USDJPY-OTC"``).
            direction: ``"call"`` for Higher, ``"put"`` for Lower.
            duration: Expiry time. Minutes for turbo, seconds for blitz.
            is_demo: Override demo flag. Defaults to the client's active mode.
            expiration_mode: ``"turbo"`` (minutes) or ``"blitz"`` (seconds).

        Returns:
            dict: Raw ``tradeOpened`` payload from the server.

        Raises:
            TradowixException: If not connected.
            TradowixTimeoutError: If the server does not confirm within 10 s.
        """
        if not self._ws or (self._ws.state is not WsState.OPEN and getattr(self._ws.state, "name", None) != "OPEN"):
            raise TradowixException("WebSocket is not connected")

        demo_flag = self._is_demo if is_demo is None else is_demo
        req_id = f"trade-{uuid.uuid4().hex}"

        slot = self._slots.order_confirm(req_id)
        slot.clear()

        trade_msg = {
            "type": "placeTrade",
            "requestId": req_id,
            "symbol": symbol,
            "direction": direction.lower(),
            "amount": amount,
            "expirationMode": expiration_mode,
            "isDemo": demo_flag,
        }
        if expiration_mode == "blitz":
            trade_msg["blitzSeconds"] = duration
        else:
            trade_msg["turboMinutes"] = duration

        logger.debug(f"Sending placeTrade: {trade_msg}")
        try:
            await self._send_ws(trade_msg)
            result = await slot.wait(timeout=10.0)
            return result
        except asyncio.TimeoutError as e:
            raise TradowixTimeoutError(
                f"Trade execution timed out for request {req_id}"
            ) from e
        finally:
            self._slots.release_order_confirm(req_id)

    async def put(
        self,
        amount: float,
        symbol: str,
        duration: int = 1,
        is_demo: Optional[bool] = None,
        expiration_mode: Literal["turbo", "blitz"] = "turbo",
    ) -> dict[str, Any]:
        """Convenience alias for ``buy(..., direction='put')``.

        Args:
            amount: Investment amount.
            symbol: Asset symbol.
            duration: Turbo expiry in minutes.
            is_demo: Override demo flag.
            expiration_mode: ``"turbo"`` (minutes) or ``"blitz"`` (seconds).

        Returns:
            dict: Raw ``tradeOpened`` payload from the server.
        """
        return await self.buy(
            amount=amount,
            symbol=symbol,
            direction="put",
            duration=duration,
            is_demo=is_demo,
            expiration_mode=expiration_mode,
        )

    async def buy_blitz(
        self,
        amount: float,
        symbol: str,
        duration_seconds: int,
        is_demo: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Place a blitz call (Higher) trade.

        Args:
            amount: Investment amount.
            symbol: Asset symbol.
            duration_seconds: Blitz duration in seconds (e.g. ``10``, ``15``, ``30``).
            is_demo: Override demo flag.

        Returns:
            dict: Raw ``tradeOpened`` payload from the server.
        """
        return await self.buy(
            amount=amount,
            symbol=symbol,
            direction="call",
            duration=duration_seconds,
            is_demo=is_demo,
            expiration_mode="blitz",
        )

    async def put_blitz(
        self,
        amount: float,
        symbol: str,
        duration_seconds: int,
        is_demo: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Place a blitz put (Lower) trade.

        Args:
            amount: Investment amount.
            symbol: Asset symbol.
            duration_seconds: Blitz duration in seconds (e.g. ``10``, ``15``, ``30``).
            is_demo: Override demo flag.

        Returns:
            dict: Raw ``tradeOpened`` payload from the server.
        """
        return await self.buy(
            amount=amount,
            symbol=symbol,
            direction="put",
            duration=duration_seconds,
            is_demo=is_demo,
            expiration_mode="blitz",
        )


    async def check_win(self, trade_id: str, timeout: float = 120.0) -> TradeResult:
        """Wait for and return the settlement result of a trade.

        Args:
            trade_id: Trade ID from the ``buy()`` / ``put()`` response (``data["id"]``).
            timeout: Maximum seconds to wait (default: ``120``).

        Returns:
            TradeResult: Typed trade settlement object.

        Raises:
            TradowixTimeoutError: If the trade does not settle within *timeout* seconds.
        """
        slot = self._slots.win_result(trade_id)

        try:
            logger.debug(f"Waiting for settlement of trade {trade_id}")
            raw_res = await slot.wait(timeout=timeout)
            return TradeResult.from_dict(raw_res)
        except asyncio.TimeoutError as e:
            raise TradowixTimeoutError(
                f"Trade resolution timed out for ID {trade_id}"
            ) from e
        finally:
            self._slots.release_win_result(trade_id)

    async def get_open_trades(
        self,
        is_demo: Optional[bool] = None,
        timeout: float = 10.0,
    ) -> List[TradeResult]:
        """Retrieve all currently active open trades.

        Args:
            is_demo: Override demo flag. Defaults to client's active mode.
            timeout: Per-request timeout in seconds (default: 10.0).

        Returns:
            list[TradeResult]: List of typed open trades.
        """
        if not self._ws or (self._ws.state is not WsState.OPEN and getattr(self._ws.state, "name", None) != "OPEN"):
            raise TradowixException("WebSocket is not connected")

        demo_flag = self._is_demo if is_demo is None else is_demo
        slot = self._slots.open_trades
        slot.clear()

        msg = {
            "type": "getOpenTrades",
            "isDemo": demo_flag,
        }

        logger.debug(f"Sending getOpenTrades: {msg}")
        try:
            await self._send_ws(msg)
            res = await slot.wait(timeout=timeout)
            raw_trades = res.get("data", [])
            return [TradeResult.from_dict(t) for t in raw_trades]
        except asyncio.TimeoutError as e:
            raise TradowixTimeoutError("getOpenTrades request timed out") from e

    async def get_trade_history(
        self,
        page: int = 1,
        page_size: int = 50,
        is_demo: Optional[bool] = None,
        timeout: float = 10.0,
    ) -> List[TradeResult]:
        """Retrieve historical settled trades.

        Args:
            page: History page number (default: 1).
            page_size: Number of items per page (default: 50).
            is_demo: Override demo flag. Defaults to client's active mode.
            timeout: Per-request timeout in seconds (default: 10.0).

        Returns:
            list[TradeResult]: List of typed historical trades.
        """
        if not self._ws or (self._ws.state is not WsState.OPEN and getattr(self._ws.state, "name", None) != "OPEN"):
            raise TradowixException("WebSocket is not connected")

        demo_flag = self._is_demo if is_demo is None else is_demo
        slot = self._slots.trade_history
        slot.clear()

        msg = {
            "type": "getTradeHistory",
            "isDemo": demo_flag,
            "page": page,
            "pageSize": page_size,
        }

        logger.debug(f"Sending getTradeHistory: {msg}")
        try:
            await self._send_ws(msg)
            res = await slot.wait(timeout=timeout)
            data = res.get("data", {})
            raw_trades = data.get("trades", [])
            return [TradeResult.from_dict(t) for t in raw_trades]
        except asyncio.TimeoutError as e:
            raise TradowixTimeoutError("getTradeHistory request timed out") from e

