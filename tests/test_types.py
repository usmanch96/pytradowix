"""Offline unit tests for pytradowix type dataclasses.

No network connection required — tests only constructors and properties.
"""
import pytest
from pytradowix.types import (
    AssetInfo,
    Balance,
    Candle,
    ProfileInfo,
    TradeResult,
    Quote,
    ReconnectPolicy,
)


# ── Candle ────────────────────────────────────────────────────────────────────

class TestCandle:
    def test_from_dict_basic(self):
        c = Candle.from_dict({"time": 1000, "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.15})
        assert c.time == 1000
        assert c.open == 1.1
        assert c.high == 1.2
        assert c.low == 1.0
        assert c.close == 1.15

    def test_from_array_converts_ms_to_seconds(self):
        # broker sends [timestamp_ms, open, high, low, close]
        c = Candle.from_array([1_000_000_000_000, 172.1, 172.2, 172.0, 172.15])
        assert c.time == 1_000_000_000  # divided by 1000

    def test_from_array_too_short_raises(self):
        with pytest.raises(ValueError, match="too short"):
            Candle.from_array([1, 2, 3])

    def test_color_green(self):
        c = Candle(time=1, open=1.0, high=1.2, low=0.9, close=1.1)
        assert c.color == "green"

    def test_color_red(self):
        c = Candle(time=1, open=1.1, high=1.2, low=0.9, close=1.0)
        assert c.color == "red"

    def test_color_doji(self):
        c = Candle(time=1, open=1.0, high=1.2, low=0.9, close=1.0)
        assert c.color == "doji"

    def test_candle_is_frozen(self):
        c = Candle(time=1, open=1.0, high=1.2, low=0.9, close=1.0)
        with pytest.raises((AttributeError, TypeError)):
            c.close = 999.0  # type: ignore[misc]


# ── Balance ───────────────────────────────────────────────────────────────────

class TestBalance:
    def test_from_dict(self):
        data = {
            "demoBalance": 10000.0,
            "realBalance": 500.0,
            "bonusBalance": 0.0,
            "currentBalance": 10000.0,
            "currency": "USD",
        }
        b = Balance.from_dict(data, is_demo=True)
        assert b.demo_balance == 10000.0
        assert b.real_balance == 500.0
        assert b.currency == "USD"
        assert b.is_demo is True

    def test_from_dict_missing_fields_default_to_zero(self):
        b = Balance.from_dict({})
        assert b.demo_balance == 0.0
        assert b.currency == "USD"


# ── ProfileInfo ───────────────────────────────────────────────────────────────

class TestProfileInfo:
    def test_from_dict(self):
        data = {
            "id": "abc123",
            "traderId": 42,
            "email": "test@example.com",
            "fullName": "Test User",
            "displayName": "Tester",
            "country": "PK",
        }
        p = ProfileInfo.from_dict(data)
        assert p.id == "abc123"
        assert p.trader_id == 42
        assert p.email == "test@example.com"
        assert p.country == "PK"
        assert p.phone is None


# ── TradeResult ───────────────────────────────────────────────────────────────

class TestTradeResult:
    def _sample(self, result: str = "win") -> dict:
        return {
            "tradeId": "trade-001",
            "userId": "user-001",
            "symbol": "USDJPY-OTC",
            "direction": "call",
            "amount": 1.0,
            "openPrice": 172.0,
            "closePrice": 172.1,
            "result": result,
            "profit": 0.92 if result == "win" else -1.0,
            "newBalance": 10000.92 if result == "win" else 9999.0,
            "openTime": "2026-01-01T00:00:00Z",
            "expiryTime": "2026-01-01T00:01:00Z",
            "closeTime": "2026-01-01T00:01:00Z",
            "duration": 60,
            "isDemo": True,
        }

    def test_from_dict_win(self):
        r = TradeResult.from_dict(self._sample("win"))
        assert r.result == "win"
        assert r.profit == 0.92
        assert r.is_demo is True

    def test_from_dict_loss(self):
        r = TradeResult.from_dict(self._sample("loss"))
        assert r.result == "loss"
        assert r.profit == -1.0

    def test_from_dict_unknown_result_maps_to_pending(self):
        data = self._sample()
        data["result"] = "unknown_status"
        r = TradeResult.from_dict(data)
        assert r.result == "pending"


# ── Quote ─────────────────────────────────────────────────────────────────────

class TestQuote:
    def test_construction(self):
        q = Quote(symbol="EURUSD", price=1.0845, timestamp=1_700_000_000.0)
        assert q.symbol == "EURUSD"
        assert q.price == 1.0845


# ── ReconnectPolicy ───────────────────────────────────────────────────────────

class TestReconnectPolicy:
    def test_defaults(self):
        p = ReconnectPolicy()
        assert p.enabled is True
        assert p.max_attempts == 0
        assert p.base_delay == 1.0
        assert p.max_delay == 30.0

    def test_disabled(self):
        p = ReconnectPolicy(enabled=False)
        assert p.enabled is False
