"""Offline unit tests for pytradowix.utils.waits.

Tests WaitableSlot and SlotRegistry in complete isolation — no network.
"""
import asyncio
import pytest
from pytradowix.utils.waits import WaitableSlot, SlotRegistry


# ── WaitableSlot ──────────────────────────────────────────────────────────────

class TestWaitableSlot:
    def test_set_and_wait(self):
        async def run():
            slot: WaitableSlot[int] = WaitableSlot()
            slot.set(42)
            result = await slot.wait(timeout=1.0)
            assert result == 42

        asyncio.run(run())

    def test_clear_resets_slot(self):
        async def run():
            slot: WaitableSlot[int] = WaitableSlot()
            slot.set(1)
            slot.clear()
            with pytest.raises(asyncio.TimeoutError):
                await slot.wait(timeout=0.05)

        asyncio.run(run())

    def test_wait_times_out_when_not_set(self):
        async def run():
            slot: WaitableSlot[str] = WaitableSlot()
            with pytest.raises(asyncio.TimeoutError):
                await slot.wait(timeout=0.05)

        asyncio.run(run())

    def test_concurrent_set_unblocks_waiter(self):
        async def run():
            slot: WaitableSlot[str] = WaitableSlot()

            async def setter():
                await asyncio.sleep(0.05)
                slot.set("hello")

            asyncio.create_task(setter())
            result = await slot.wait(timeout=1.0)
            assert result == "hello"

        asyncio.run(run())


# ── SlotRegistry ──────────────────────────────────────────────────────────────

class TestSlotRegistry:
    def test_balance_slot(self):
        async def run():
            reg = SlotRegistry()
            reg.balance.set({"demo": 100.0})
            val = await reg.balance.wait(timeout=0.5)
            assert val == {"demo": 100.0}

        asyncio.run(run())

    def test_keyed_order_confirm_slot(self):
        async def run():
            reg = SlotRegistry()
            slot = reg.order_confirm("req-001")
            slot.set({"id": "trade-001"})
            val = await reg.order_confirm("req-001").wait(timeout=0.5)
            assert val["id"] == "trade-001"
            reg.release_order_confirm("req-001")
            assert "req-001" not in reg._order_confirm

        asyncio.run(run())

    def test_keyed_win_result_slot(self):
        async def run():
            reg = SlotRegistry()
            slot = reg.win_result("trade-abc")
            slot.set({"result": "win"})
            val = await reg.win_result("trade-abc").wait(timeout=0.5)
            assert val["result"] == "win"
            reg.release_win_result("trade-abc")

        asyncio.run(run())

    def test_keyed_candle_history_slot(self):
        async def run():
            reg = SlotRegistry()
            slot = reg.candle_history("history-001")
            slot.set({"candles": [[1000000, 1.0, 1.1, 0.9, 1.05]]})
            val = await reg.candle_history("history-001").wait(timeout=0.5)
            assert len(val["candles"]) == 1
            reg.release_candle_history("history-001")
            assert "history-001" not in reg._candle_history

        asyncio.run(run())

    def test_different_keys_are_independent(self):
        async def run():
            reg = SlotRegistry()
            reg.order_confirm("a").set({"a": 1})
            reg.order_confirm("b").set({"b": 2})
            a = await reg.order_confirm("a").wait(timeout=0.5)
            b = await reg.order_confirm("b").wait(timeout=0.5)
            assert a == {"a": 1}
            assert b == {"b": 2}

        asyncio.run(run())
