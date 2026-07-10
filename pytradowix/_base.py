"""Internal Protocol base that gives type checkers visibility into the
shared attributes every mixin relies on.

Mixin classes inherit from ``_ClientBase`` so Pylance / mypy understand
attribute accesses like ``self._ws``, ``self._slots``, ``self._send_ws()``,
etc. without requiring circular imports.

This module is **not** part of the public API — it exists purely for typing.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union

import httpx
from websockets.asyncio.client import ClientConnection

from pytradowix.utils.waits import SlotRegistry
from pytradowix.types import Quote, ReconnectPolicy


class _ClientBase:
    """Declares all instance attributes that the mixin API methods share.

    Every mixin (AccountMixin, TradingMixin, RealtimeMixin, HistoryMixin)
    inherits from this class so the type checker can resolve attribute
    lookups on ``self``.

    The concrete ``Tradowix`` class provides the actual implementations;
    this base only carries type annotations.
    """

    # ── Connection state ──────────────────────────────────────────────────
    _email: str
    _password: str
    _is_demo: bool
    _base_url: str
    _ws_url: str
    _user_agent: str
    _session_token: Optional[str]

    _session: Optional[httpx.AsyncClient]
    _ws: Optional[ClientConnection]

    reconnect_policy: ReconnectPolicy

    # ── Event slots ───────────────────────────────────────────────────────
    _slots: SlotRegistry

    # ── Cached server data ────────────────────────────────────────────────
    _balance_data: Dict[str, Any]
    _profile_data: Optional[Dict[str, Any]]

    instruments: List[Dict[str, Any]]
    quotes: Dict[str, Quote]
    on_quote: Optional[Callable[[Quote], Union[None, Any]]]

    # ── Internal helpers (implemented in client.py) ───────────────────────
    async def _send_ws(self, payload: Dict[str, Any]) -> None: ...
    async def _start_ws(self) -> None: ...
    async def _stop_ws(self) -> None: ...
