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
from pytradowix._api.account import AccountMixin

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


# ── Asset Tradability ─────────────────────────────────────────────────────────

class DummyClient(AccountMixin):
    def __init__(self, instruments: list[dict]):
        self.instruments = instruments
        self._is_demo = True

class TestAssetTradability:
    def test_is_asset_tradable_active_and_open(self):
        client = DummyClient([
            {
                "id": "1",
                "symbol": "EURUSD",
                "name": "EURUSD",
                "displayName": "EURUSD",
                "category": "Forex",
                "groupName": "Currency pairs",
                "precision": 5,
                "isActive": True,
                "isOtc": False,
                "turboPayout": 0.8,
                "blitzPayout": 0.8,
                "isOpen": True,
            }
        ])
        assert client.is_asset_tradable("EURUSD") is True

    def test_is_asset_tradable_inactive(self):
        client = DummyClient([
            {
                "id": "1",
                "symbol": "EURUSD",
                "name": "EURUSD",
                "displayName": "EURUSD",
                "category": "Forex",
                "groupName": "Currency pairs",
                "precision": 5,
                "isActive": False,
                "isOtc": False,
                "turboPayout": 0.8,
                "blitzPayout": 0.8,
                "isOpen": True,
            }
        ])
        assert client.is_asset_tradable("EURUSD") is False

    def test_is_asset_tradable_closed(self):
        client = DummyClient([
            {
                "id": "1",
                "symbol": "EURUSD",
                "name": "EURUSD",
                "displayName": "EURUSD",
                "category": "Forex",
                "groupName": "Currency pairs",
                "precision": 5,
                "isActive": True,
                "isOtc": False,
                "turboPayout": 0.8,
                "blitzPayout": 0.8,
                "isOpen": False,
            }
        ])
        assert client.is_asset_tradable("EURUSD") is False

    def test_is_asset_tradable_missing_symbol(self):
        client = DummyClient([])
        assert client.is_asset_tradable("EURUSD") is False


# ── Event Callbacks ───────────────────────────────────────────────────────────

class TestEventCallbacks:
    @pytest.mark.asyncio
    async def test_trigger_callback_sync(self):
        from pytradowix import Tradowix
        client = Tradowix(email="test@email.com", password="password")
        called = False

        def on_connect_cb():
            nonlocal called
            called = True

        client.on_connect = on_connect_cb
        await client._trigger_callback(client.on_connect)
        assert called

    @pytest.mark.asyncio
    async def test_trigger_callback_async(self):
        from pytradowix import Tradowix
        client = Tradowix(email="test@email.com", password="password")
        called = False

        async def on_connect_cb():
            nonlocal called
            called = True

        client.on_connect = on_connect_cb
        await client._trigger_callback(client.on_connect)
        assert called

    @pytest.mark.asyncio
    async def test_trigger_balance_update(self):
        from pytradowix import Tradowix
        client = Tradowix(email="test@email.com", password="password")
        received_balance = None

        def on_balance_cb(bal: Balance):
            nonlocal received_balance
            received_balance = bal

        client.on_balance_update = on_balance_cb
        test_bal = Balance(
            demo_balance=100.0,
            real_balance=0.0,
            bonus_balance=0.0,
            current_balance=100.0,
            currency="USD",
            is_demo=True,
        )
        await client._trigger_callback(client.on_balance_update, test_bal)
        assert received_balance == test_bal

    @pytest.mark.asyncio
    async def test_trigger_trade_settled(self):
        from pytradowix import Tradowix
        client = Tradowix(email="test@email.com", password="password")
        received_result = None

        def on_trade_cb(res: TradeResult):
            nonlocal received_result
            received_result = res

        client.on_trade_settled = on_trade_cb
        test_res = TradeResult(
            trade_id="t-001",
            user_id="u-001",
            symbol="USDJPY-OTC",
            direction="call",
            amount=1.0,
            open_price=100.0,
            close_price=101.0,
            result="win",
            profit=0.92,
            new_balance=100.92,
            open_time="",
            expiry_time="",
            close_time="",
            duration=60,
            is_demo=True,
        )
        await client._trigger_callback(client.on_trade_settled, test_res)
        assert received_result == test_res


# ── Blitz Trading ─────────────────────────────────────────────────────────────

class TestBlitzTrading:
    @pytest.mark.asyncio
    async def test_buy_turbo_payload(self, monkeypatch):
        from typing import Any, cast
        from pytradowix import Tradowix
        client = Tradowix(email="test@email.com", password="password")
        
        # Mock ws
        class MockWs:
            class MockState:
                name = "OPEN"
            state = MockState()
        client._ws = cast(Any, MockWs())

        sent_payload = None

        async def mock_send_ws(payload):
            nonlocal sent_payload
            sent_payload = payload
            req_id = payload["requestId"]
            client._slots.order_confirm(req_id).set({"id": "trade-123", "openPrice": 1.23})

        monkeypatch.setattr(client, "_send_ws", mock_send_ws)

        res = await client.buy(amount=10.0, symbol="EURUSD", direction="call", duration=5, expiration_mode="turbo")
        assert res["id"] == "trade-123"
        assert sent_payload is not None
        assert sent_payload["expirationMode"] == "turbo"
        assert sent_payload["turboMinutes"] == 5
        assert "blitzSeconds" not in sent_payload

    @pytest.mark.asyncio
    async def test_buy_blitz_payload(self, monkeypatch):
        from typing import Any, cast
        from pytradowix import Tradowix
        client = Tradowix(email="test@email.com", password="password")

        class MockWs:
            class MockState:
                name = "OPEN"
            state = MockState()
        client._ws = cast(Any, MockWs())

        sent_payload = None

        async def mock_send_ws(payload):
            nonlocal sent_payload
            sent_payload = payload
            req_id = payload["requestId"]
            client._slots.order_confirm(req_id).set({"id": "trade-456", "openPrice": 1.23})

        monkeypatch.setattr(client, "_send_ws", mock_send_ws)

        res = await client.buy_blitz(amount=10.0, symbol="EURUSD", duration_seconds=15)
        assert res["id"] == "trade-456"
        assert sent_payload is not None
        assert sent_payload["expirationMode"] == "blitz"
        assert sent_payload["blitzSeconds"] == 15
        assert "turboMinutes" not in sent_payload


# ── Clock Synchronization ─────────────────────────────────────────────────────

class TestTimeSync:
    @pytest.mark.asyncio
    async def test_time_sync_offset_calculation(self, monkeypatch):
        import time
        from pytradowix import Tradowix
        client = Tradowix(email="test@email.com", password="password")
        
        assert client._server_time_offset == 0.0
        
        local_time_mock = 1000.0
        monkeypatch.setattr(time, "time", lambda: local_time_mock)
        
        time_sync_frame = {
            "type": "timeSync",
            "data": {
                "timestamp": 1005000
            }
        }
        await client._handle_ws_message(time_sync_frame)
        
        assert client._server_time_offset == 5.0
        assert client.get_server_time() == 1005.0


# ── History and Open Trades Retrieval ─────────────────────────────────────────

class TestHistoryAndOpenTrades:
    @pytest.mark.asyncio
    async def test_get_open_trades(self, monkeypatch):
        from typing import Any, cast
        from pytradowix import Tradowix
        client = Tradowix(email="test@email.com", password="password")

        class MockWs:
            class MockState:
                name = "OPEN"
            state = MockState()
        client._ws = cast(Any, MockWs())

        sent_payload: Any = None

        async def mock_send_ws(payload):
            nonlocal sent_payload
            sent_payload = payload
            client._slots.open_trades.set({
                "type": "openTrades",
                "data": [
                    {
                        "id": "t-open-01",
                        "userId": "u-01",
                        "symbol": "EURUSD",
                        "direction": "call",
                        "amount": 10.0,
                        "openPrice": 1.1234,
                        "result": "pending",
                        "isDemo": True,
                    }
                ]
            })

        monkeypatch.setattr(client, "_send_ws", mock_send_ws)

        res = await client.get_open_trades()
        assert len(res) == 1
        assert res[0].trade_id == "t-open-01"
        assert res[0].symbol == "EURUSD"
        assert res[0].result == "pending"
        assert sent_payload["type"] == "getOpenTrades"
        assert sent_payload["isDemo"] is True

    @pytest.mark.asyncio
    async def test_get_trade_history(self, monkeypatch):
        from typing import Any, cast
        from pytradowix import Tradowix
        client = Tradowix(email="test@email.com", password="password")

        class MockWs:
            class MockState:
                name = "OPEN"
            state = MockState()
        client._ws = cast(Any, MockWs())

        sent_payload: Any = None

        async def mock_send_ws(payload):
            nonlocal sent_payload
            sent_payload = payload
            client._slots.trade_history.set({
                "type": "tradeHistory",
                "data": {
                    "trades": [
                        {
                            "id": "t-hist-01",
                            "userId": "u-01",
                            "symbol": "GBPUSD",
                            "direction": "put",
                            "amount": 5.0,
                            "openPrice": 1.3456,
                            "closePrice": 1.3450,
                            "result": "win",
                            "profit": 4.60,
                            "isDemo": True,
                        }
                    ],
                    "totalCount": 1,
                    "page": 1,
                    "pageSize": 50,
                }
            })

        monkeypatch.setattr(client, "_send_ws", mock_send_ws)

        res = await client.get_trade_history(page=1, page_size=10)
        assert len(res) == 1
        assert res[0].trade_id == "t-hist-01"
        assert res[0].symbol == "GBPUSD"
        assert res[0].result == "win"
        assert res[0].profit == 4.60
        assert sent_payload["type"] == "getTradeHistory"
        assert sent_payload["page"] == 1
        assert sent_payload["pageSize"] == 10


# ── Payout Filtering ──────────────────────────────────────────────────────────

class TestPayoutFiltering:
    def test_get_highest_payout_assets(self):
        client = DummyClient([
            {
                "id": "1",
                "symbol": "EURUSD",
                "name": "EURUSD",
                "displayName": "EURUSD",
                "category": "Forex",
                "groupName": "Currency pairs",
                "precision": 5,
                "isActive": True,
                "isOtc": False,
                "turboPayout": 0.82,
                "blitzPayout": 0.70,
                "isOpen": True,
            },
            {
                "id": "2",
                "symbol": "GBPUSD",
                "name": "GBPUSD",
                "displayName": "GBPUSD",
                "category": "Forex",
                "groupName": "Currency pairs",
                "precision": 5,
                "isActive": True,
                "isOtc": False,
                "turboPayout": 0.90,
                "blitzPayout": 0.85,
                "isOpen": True,
            },
            {
                "id": "3",
                "symbol": "USDJPY",
                "name": "USDJPY",
                "displayName": "USDJPY",
                "category": "Forex",
                "groupName": "Currency pairs",
                "precision": 3,
                "isActive": False,
                "isOtc": False,
                "turboPayout": 0.95,
                "blitzPayout": 0.95,
                "isOpen": True,
            },
            {
                "id": "4",
                "symbol": "AUDUSD",
                "name": "AUDUSD",
                "displayName": "AUDUSD",
                "category": "Forex",
                "groupName": "Currency pairs",
                "precision": 5,
                "isActive": True,
                "isOtc": False,
                "turboPayout": 0.75,
                "blitzPayout": 0.60,
                "isOpen": True,
            }
        ])

        turbo_assets = client.get_highest_payout_assets(min_payout=0.80, mode="turbo")
        assert len(turbo_assets) == 2
        assert turbo_assets[0].symbol == "GBPUSD"
        assert turbo_assets[1].symbol == "EURUSD"

        blitz_assets = client.get_highest_payout_assets(min_payout=0.80, mode="blitz")
        assert len(blitz_assets) == 1
        assert blitz_assets[0].symbol == "GBPUSD"






