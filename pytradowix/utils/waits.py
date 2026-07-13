from __future__ import annotations
import asyncio
import random
from typing import Callable, Generic, TypeVar, Dict, Any

T = TypeVar("T")

DEFAULT_TIMEOUT: float = 10.0

class WaitableSlot(Generic[T]):
    """Typed slot a consumer awaits and the producer fills via .set()."""

    __slots__ = ("_value", "_event")

    def __init__(self) -> None:
        self._value: T | None = None
        self._event: asyncio.Event | None = None

    def _get_event(self) -> asyncio.Event:
        if self._event is None:
            self._event = asyncio.Event()
        return self._event

    def set(self, value: T) -> None:
        """Store the value and wake any awaiting consumers."""
        if value is None:
            raise ValueError("WaitableSlot.set() does not accept None; use clear() to reset")
        self._value = value
        self._get_event().set()

    def clear(self) -> None:
        """Reset the slot so subsequent waits block again."""
        self._value = None
        if self._event is not None:
            self._event.clear()

    @property
    def value(self) -> T | None:
        """Return the current value without blocking."""
        return self._value

    def is_set(self) -> bool:
        """Return True if the slot currently holds a value."""
        return self._event is not None and self._event.is_set()

    async def wait(self, timeout: float = DEFAULT_TIMEOUT) -> T:
        """Block until set or raise asyncio.TimeoutError on timeout."""
        await asyncio.wait_for(self._get_event().wait(), timeout=timeout)
        assert self._value is not None, "WaitableSlot: event set but _value is None"
        return self._value  # type: ignore[return-value]


async def wait_until(
    predicate: Callable[[], bool],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    poll_interval: float = 0.05,
) -> None:
    """Poll predicate() until truthy or raise asyncio.TimeoutError."""
    async def _loop() -> None:
        while not predicate():
            await asyncio.sleep(poll_interval)

    await asyncio.wait_for(_loop(), timeout=timeout)


async def backoff_sleep(
    attempt: int,
    *,
    base: float = 1.0,
    cap: float = 30.0,
    jitter: float = 0.1,
) -> None:
    """Sleep for an exponentially increasing duration with jitter."""
    delay = min(cap, base * (2 ** attempt))
    delay = delay * (1.0 + random.uniform(-jitter, jitter))
    await asyncio.sleep(max(0.0, delay))


class SlotRegistry:
    """Container of named and keyed WaitableSlots used by TradowixAPI."""

    def __init__(self) -> None:
        # Named slots
        self.balance: WaitableSlot[Dict[str, Any]] = WaitableSlot()
        self.open_trades: WaitableSlot[Dict[str, Any]] = WaitableSlot()
        self.trade_history: WaitableSlot[Dict[str, Any]] = WaitableSlot()

        # Keyed slots (created on demand)
        self._order_confirm: Dict[str, WaitableSlot[Dict[str, Any]]] = {}
        self._win_result: Dict[str, WaitableSlot[Dict[str, Any]]] = {}
        self._candle_history: Dict[str, WaitableSlot[Dict[str, Any]]] = {}
        self._chart_load: Dict[str, WaitableSlot[Dict[str, Any]]] = {}

    def order_confirm(self, request_id: str) -> WaitableSlot[Dict[str, Any]]:
        slot = self._order_confirm.get(request_id)
        if slot is None:
            slot = WaitableSlot()
            self._order_confirm[request_id] = slot
        return slot

    def release_order_confirm(self, request_id: str) -> None:
        self._order_confirm.pop(request_id, None)

    def win_result(self, trade_id: str) -> WaitableSlot[Dict[str, Any]]:
        slot = self._win_result.get(trade_id)
        if slot is None:
            slot = WaitableSlot()
            self._win_result[trade_id] = slot
        return slot

    def release_win_result(self, trade_id: str) -> None:
        self._win_result.pop(trade_id, None)

    def candle_history(self, request_id: str) -> WaitableSlot[Dict[str, Any]]:
        slot = self._candle_history.get(request_id)
        if slot is None:
            slot = WaitableSlot()
            self._candle_history[request_id] = slot
        return slot

    def release_candle_history(self, request_id: str) -> None:
        self._candle_history.pop(request_id, None)

    # Initial chart load triggered by subscribeTicks (no requestId)
    def chart_load(self, symbol: str) -> WaitableSlot[Dict[str, Any]]:
        target_slot = self._chart_load.get(symbol)
        if target_slot is None:
            target_slot = WaitableSlot()
            self._chart_load[symbol] = target_slot
        return target_slot

    def release_chart_load(self, symbol: str) -> None:
        self._chart_load.pop(symbol, None)

