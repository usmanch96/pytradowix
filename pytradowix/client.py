import asyncio
import inspect
import json
import logging
import time
from typing import Optional, Dict, Any, List, Callable, Union

import httpx
import websockets
from websockets.asyncio.client import ClientConnection
from websockets.protocol import State as WsState
from websockets.exceptions import ConnectionClosed

from pytradowix._api.account import AccountMixin
from pytradowix._api.trading import TradingMixin
from pytradowix._api.realtime import RealtimeMixin
from pytradowix._api.history import HistoryMixin
from pytradowix.utils.waits import SlotRegistry
from pytradowix.types import Quote, ReconnectPolicy, Balance, TradeResult, Candle
from pytradowix.exceptions import TradowixException, TradowixAuthError
from pytradowix.utils.candles import CandleAggregator

logger = logging.getLogger(__name__)

class Tradowix(AccountMixin, TradingMixin, RealtimeMixin, HistoryMixin):
    """The unified TradoWix API Client.

    Args:
        email: TradoWix account email.
        password: TradoWix account password.
        is_demo: Trade on demo account by default (default: ``True``).
        base_url: TradoWix REST API base URL.
        ws_url: TradoWix WebSocket endpoint URL.
        user_agent: Browser user-agent string for HTTP/WS headers.
        reconnect_policy: Auto-reconnect behaviour on dropped connection.
            Pass ``ReconnectPolicy(enabled=False)`` to disable.
    """

    def __init__(
        self,
        email: str,
        password: str,
        is_demo: bool = True,
        base_url: str = "https://tradowix.com",
        ws_url: str = "wss://api.tradowix.com/ws",
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        reconnect_policy: Optional[ReconnectPolicy] = None,
    ) -> None:
        self._email = email
        self._password = password
        self._is_demo = is_demo
        self._base_url = base_url
        self._ws_url = ws_url
        self.reconnect_policy: ReconnectPolicy = reconnect_policy or ReconnectPolicy()
        from pytradowix.config import load_session
        session_info = load_session(email, user_agent)
        self._session_token = session_info.get("token")
        self._user_agent = session_info.get("user_agent", user_agent)

        self._session: Optional[httpx.AsyncClient] = None
        self._ws: Optional[ClientConnection] = None

        self._ws_task: Optional[asyncio.Task[None]] = None
        self._ping_task: Optional[asyncio.Task[None]] = None

        self._slots = SlotRegistry()
        self._balance_data: Dict[str, Any] = {}
        self._profile_data: Optional[Dict[str, Any]] = None

        self.instruments: List[Dict[str, Any]] = []
        self.quotes: Dict[str, Quote] = {}
        self.on_quote: Optional[Callable[[Quote], Union[None, Any]]] = None
        self.on_connect: Optional[Callable[[], Union[None, Any]]] = None
        self.on_disconnect: Optional[Callable[[], Union[None, Any]]] = None
        self.on_balance_update: Optional[Callable[[Balance], Union[None, Any]]] = None
        self.on_trade_settled: Optional[Callable[[TradeResult], Union[None, Any]]] = None
        self.on_candle_update: Optional[Callable[[str, int, Candle, bool], Union[None, Any]]] = None
        self._candle_aggregators: Dict[str, Dict[int, CandleAggregator]] = {}
        self._server_time_offset: float = 0.0
        self._subscribed_symbols: set[str] = set()

    async def _send_ws(self, payload: Dict[str, Any]) -> None:
        """Send a JSON payload over the WebSocket."""
        if self._ws is None or self._ws.state is not WsState.OPEN:
            raise TradowixException("WebSocket is not connected")
        await self._ws.send(json.dumps(payload))

    async def ping(self) -> None:
        """Send a keep-alive ping frame to the server."""
        req_id = f"ping-{int(time.time() * 1000)}"
        await self._send_ws({"type": "ping", "requestId": req_id})

    async def _start_ws(self) -> None:
        """Establish WebSocket connection and handle post-connection authentication handshake."""
        headers = {
            "Origin": "https://tradowix.com",
            "User-Agent": self._user_agent,
            "Cookie": f"session-token={self._session_token}"
        }
        
        logger.info(f"Connecting to WebSocket at {self._ws_url}...")
        try:
            self._ws = await websockets.connect(
                self._ws_url,
                additional_headers=headers
            )
        except Exception as e:
            raise TradowixException(f"WebSocket connection failed: {e}") from e

        # Wait for the server's initial "authRequired" frame
        try:
            recv_init = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
            init_frame = recv_init.decode("utf-8") if isinstance(recv_init, bytes) else recv_init
            init_data = json.loads(init_frame)
            if init_data.get("type") != "authRequired":
                raise TradowixException(f"Expected authRequired frame, got: {init_frame}")
        except Exception as e:
            await self._ws.close()
            self._ws = None
            raise TradowixException(f"WebSocket handshake protocol violation: {e}") from e

        # Send authentication handshake
        auth_msg = {
            "type": "authenticate",
            "token": self._session_token
        }
        logger.debug(f"Sending WS auth handshake: {auth_msg}")
        await self._ws.send(json.dumps(auth_msg))

        # Wait for "authenticated" confirmation
        try:
            recv_auth = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
            auth_frame = recv_auth.decode("utf-8") if isinstance(recv_auth, bytes) else recv_auth
            auth_data = json.loads(auth_frame)
            if auth_data.get("type") != "authenticated":
                raise TradowixAuthError(f"WebSocket auth handshake rejected: {auth_frame}")
            logger.info("WebSocket authenticated successfully!")
        except Exception as e:
            await self._ws.close()
            self._ws = None
            if isinstance(e, TradowixAuthError):
                raise
            raise TradowixException(f"WebSocket auth confirmation failed: {e}") from e

        # Spawn background loops first so they can handle incoming messages
        self._ws_task = asyncio.create_task(self._ws_recv_loop())
        self._ping_task = asyncio.create_task(self._ws_ping_loop())

        # Trigger getBalance request immediately to populate instrument and balance caches
        await self._send_ws({"type": "getBalance"})

        # Wait for the initial balanceUpdate to populate our caches
        try:
            await self._slots.balance.wait(timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for initial balance update during connection")

        await self._trigger_callback(self.on_connect)

    async def _ws_ping_loop(self) -> None:
        """Background loop to send keep-alive pings."""
        try:
            while self._ws is not None and self._ws.state is WsState.OPEN:
                await asyncio.sleep(10.0)
                await self.ping()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"WS ping loop encountered error: {e}")

    async def _ws_recv_loop(self) -> None:
        """Background receiver loop with optional auto-reconnect on ConnectionClosed."""
        attempt = 0
        while True:
            try:
                while self._ws is not None and self._ws.state is WsState.OPEN:
                    recv_frame = await self._ws.recv()
                    frame = recv_frame.decode("utf-8") if isinstance(recv_frame, bytes) else recv_frame
                    try:
                        msg = json.loads(frame)
                        await self._handle_ws_message(msg)
                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON frame: {frame}")
                    except Exception as e:
                        logger.error(f"Error handling WS message: {e}", exc_info=True)
                # Connection dropped cleanly
                break
            except ConnectionClosed:
                logger.info("WebSocket connection closed by remote.")
                await self._trigger_callback(self.on_disconnect)
                if not self.reconnect_policy.enabled:
                    break
                attempt += 1
                max_att = self.reconnect_policy.max_attempts
                if max_att > 0 and attempt > max_att:
                    logger.error(f"Max reconnect attempts ({max_att}) reached. Giving up.")
                    break
                delay = min(
                    self.reconnect_policy.base_delay * (2 ** (attempt - 1)),
                    self.reconnect_policy.max_delay,
                )
                logger.info(f"Reconnecting in {delay:.1f}s (attempt {attempt})...")
                await asyncio.sleep(delay)
                try:
                    await self.connect()
                    attempt = 0  # reset on success
                    logger.info("Reconnected successfully.")
                    return  # new loop started by connect() -> _start_ws()
                except Exception as e:
                    logger.error(f"Reconnect attempt {attempt} failed: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WS receiver loop error: {e}", exc_info=True)
                break

    async def _handle_ws_message(self, msg: Dict[str, Any]) -> None:
        """Route parsed JSON message to their respective handlers or slots."""
        server_ts = msg.get("timestamp")
        if server_ts is not None:
            self._server_time_offset = (float(server_ts) / 1000.0) - time.time()

        m_type = msg.get("type")
        
        if m_type == "balanceUpdate":
            data = msg.get("data", {})
            self._balance_data = data.get("balance", {})
            self._slots.balance.set(self._balance_data)
            await self._trigger_callback(
                self.on_balance_update,
                Balance.from_dict(self._balance_data, is_demo=self._is_demo)
            )
            
        elif m_type == "instruments":
            self.instruments = msg.get("data", [])
            
        elif m_type == "quote":
            data = msg.get("data", {})
            symbol = data.get("symbol")
            price = data.get("price")
            ts = data.get("timestamp", time.time() * 1000)
            if symbol and price is not None:
                quote = Quote(symbol=symbol, price=float(price), timestamp=float(ts) / 1000.0)
                self.quotes[symbol] = quote
                await self._trigger_quote_callback(quote)
                
        elif m_type == "tickUpdate":
            data = msg.get("data", {})
            symbol = data.get("symbol")
            tick = data.get("tick", [])
            if symbol and len(tick) >= 2:
                price = tick[0]
                ts = tick[1]
                quote = Quote(symbol=symbol, price=float(price), timestamp=float(ts) / 1000.0)
                self.quotes[symbol] = quote
                await self._trigger_quote_callback(quote)
                
        elif m_type == "tradeOpened":
            logger.info(f"Received tradeOpened: {msg}")
            req_id = msg.get("requestId")
            if req_id:
                self._slots.order_confirm(req_id).set(msg.get("data", {}))
                
        elif m_type == "tradeResultsBatch":
            logger.info(f"Received tradeResultsBatch: {msg}")
            results = msg.get("data", [])
            for res in results:
                trade_id = res.get("tradeId")
                if trade_id:
                    self._slots.win_result(trade_id).set(res)
                await self._trigger_callback(self.on_trade_settled, TradeResult.from_dict(res))
                    
        elif m_type == "candleHistory":
            req_id = msg.get("requestId")
            if req_id:
                self._slots.candle_history(req_id).set(msg.get("data", {}))
            else:
                data = msg.get("data", {})
                symbol = data.get("symbol")
                if symbol:
                    self._slots.chart_load(symbol).set(data)

        elif m_type == "openTrades":
            self._slots.open_trades.set(msg)

        elif m_type == "tradeHistory":
            self._slots.trade_history.set(msg)

        elif m_type == "timeSync":
            data = msg.get("data", {})
            server_time_ms = data.get("timestamp") or msg.get("timestamp")
            if server_time_ms is not None:
                self._server_time_offset = (float(server_time_ms) / 1000.0) - time.time()

    async def _trigger_quote_callback(self, quote: Quote) -> None:
        """Safely fire the user-registered on_quote callback and aggregate candle updates."""
        await self._trigger_callback(self.on_quote, quote)

        symbol = quote.symbol
        if symbol in self._candle_aggregators:
            for period, aggregator in self._candle_aggregators[symbol].items():
                candle, is_closed = aggregator.add_tick(quote.price, quote.timestamp)
                await self._trigger_callback(self.on_candle_update, symbol, period, candle, is_closed)

    async def _trigger_callback(self, cb: Optional[Callable[..., Any]], *args: Any) -> None:
        """Safely fire a user-registered callback whether sync or async."""
        if cb:
            try:
                if inspect.iscoroutinefunction(cb):
                    await cb(*args)
                else:
                    cb(*args)
            except Exception as e:
                logger.error(f"Error in user callback: {e}", exc_info=True)

    async def _stop_ws(self) -> None:
        """Cancel background tasks and close connection."""
        had_ws = self._ws is not None
        if self._ws_task is not None:
            self._ws_task.cancel()
            self._ws_task = None
        if self._ping_task is not None:
            self._ping_task.cancel()
            self._ping_task = None
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        if had_ws:
            await self._trigger_callback(self.on_disconnect)

    def get_server_time(self) -> float:
        """Return the estimated server epoch timestamp in seconds."""
        return time.time() + self._server_time_offset
