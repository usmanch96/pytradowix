# 🚀 PyTradoWix

<p align="center">
  <i>Unofficial Python client for the TradoWix binary options trading platform.</i>
</p>
<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue" alt="Python Versions"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/typing-strict-purple" alt="Typing"/>
</p>

---

## 📘 About

**pytradowix** is an async Python wrapper for the [TradoWix](https://tradowix.com) WebSocket trading API. It lets you authenticate, stream live prices, fetch unlimited historical candle data, and place / monitor binary option trades — all from clean, typed Python code.

> ⚠️ This library is **not a trading bot** and makes no trading decisions. It is a developer tool.

---

## 🛠 Installation

```bash
# From source (recommended during development)
git clone https://github.com/usmanch96/pytradowix.git
cd pytradowix
pip install -e .

# Install dev extras (pytest, mypy)
pip install -e ".[dev]"
```

---

## ⚡ Quick Start

```python
import asyncio
import os
from dotenv import load_dotenv
from pytradowix import Tradowix

load_dotenv()

async def main():
    client = Tradowix(
        email=os.getenv("TRADOWIX_EMAIL"),
        password=os.getenv("TRADOWIX_PASSWORD"),
        is_demo=True,  # trade on demo account
    )

    await client.connect()

    # Account info
    profile = client.get_profile()
    balance = client.get_balance()
    print(f"Hello {profile.display_name}! Balance: {balance.current_balance} {balance.currency}")

    # Historical candles (1 week of 1-minute bars)
    candles = await client.get_historical_candles(
        symbol="USDJPY-OTC",
        amount_of_seconds=604800,  # 7 days
        period=60,                  # 1-minute bars
    )
    print(f"Fetched {len(candles)} candles. Oldest: {candles[0]}, Newest: {candles[-1]}")

    # Subscribe to live prices
    def on_tick(quote):
        print(f"[TICK] {quote.symbol}: {quote.price}")

    client.on_quote = on_tick
    await client.subscribe_ticks("USDJPY-OTC")
    await asyncio.sleep(5)

    # Place a trade
    trade = await client.buy(amount=1.0, symbol="USDJPY-OTC", direction="call", duration=1)
    trade_id = trade["id"]
    print(f"Trade placed: {trade_id}")

    # Wait for settlement
    result = await client.check_win(trade_id, timeout=120.0)
    print(f"Result: {result.result.upper()}, P&L: ${result.profit}")

    await client.close()

asyncio.run(main())
```

---

## 💡 API Reference

| Method | Description |
|---|---|
| `connect()` | Authenticate and establish WebSocket connection |
| `close()` | Gracefully disconnect |
| `get_profile()` | Returns `ProfileInfo` — user profile data |
| `get_balance()` | Returns `Balance` — demo/real/bonus balances |
| `get_assets()` | Returns `list[AssetInfo]` — all tradeable instruments |
| `change_account(mode)` | Switch between `"demo"` and `"real"` account modes |
| `edit_demo_balance(amount)` | Request a demo balance top-up |
| `subscribe_ticks(symbol)` | Start receiving live `Quote` ticks for a symbol |
| `unsubscribe_ticks(symbol)` | Stop receiving ticks for a symbol |
| `get_candles(symbol, end_from_time, minutes, timeframe)` | Fetch a single batch of historical candles |
| `get_historical_candles(symbol, amount_of_seconds, period)` | Fetch unlimited history via backward pagination |
| `buy(amount, symbol, direction, duration)` | Place a call/put trade |
| `put(amount, symbol, duration)` | Convenience alias for `buy(..., direction="put")` |
| `check_win(trade_id, timeout)` | Wait for and return a `TradeResult` |

---

## 📦 Typed Data Classes

All public methods return typed, frozen dataclasses — no more opaque dicts.

```python
from pytradowix import Candle, Balance, TradeResult, Quote, AssetInfo, ProfileInfo
```

| Type | Fields |
|---|---|
| `Candle` | `time`, `open`, `high`, `low`, `close`, `.color` |
| `Balance` | `demo_balance`, `real_balance`, `current_balance`, `currency`, `is_demo` |
| `ProfileInfo` | `id`, `email`, `full_name`, `display_name`, `country`, ... |
| `AssetInfo` | `symbol`, `name`, `is_open`, `is_otc`, `turbo_payout_rate`, ... |
| `TradeResult` | `trade_id`, `result`, `profit`, `new_balance`, `direction`, ... |
| `Quote` | `symbol`, `price`, `timestamp` |

---

## 🔄 Auto-Reconnect

The client supports automatic reconnection with exponential backoff:

```python
from pytradowix import Tradowix, ReconnectPolicy

client = Tradowix(
    email="...",
    password="...",
    reconnect_policy=ReconnectPolicy(
        enabled=True,
        max_attempts=0,   # 0 = infinite retries
        base_delay=1.0,
        max_delay=30.0,
    ),
)
```

---

## 🔒 Session Caching

The client automatically caches session tokens to `~/.pytradowix/session.json` in the user's home directory. On the next run, the cached token is validated with a lightweight profile request before falling back to a full credential login. This avoids unnecessary authentication round-trips.

---

## 🧪 Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 📁 Project Structure

```
pytradowix/
├── __init__.py          # Public API surface
├── client.py            # Core Tradowix client class
├── config.py            # Session caching configuration
├── exceptions.py        # Custom exception hierarchy
├── types.py             # Typed frozen dataclasses
├── py.typed             # PEP 561 type marker
├── utils/
│   └── waits.py         # Async slot registry for WS event coordination
└── _api/
    ├── account.py       # connect, profile, balance, change_account
    ├── trading.py       # buy, put, check_win
    ├── realtime.py      # subscribe/unsubscribe ticks
    └── history.py       # get_candles, get_historical_candles
examples/
├── fetch_balance.py
├── place_trade.py
└── fetch_history.py
tests/
├── test_types.py
└── test_waits.py
```

---

## ⚙️ Environment Variables

Copy the template `.env.example` to `.env` in the project root and fill in your credentials:

```bash
cp .env.example .env
```

`.env` structure:
```env
TRADOWIX_EMAIL=your@email.com
TRADOWIX_PASSWORD=yourpassword
```

---

## 💬 Contact

For questions, feedback, or custom integrations:
- **Telegram**: [@usmanch069](https://t.me/usmanch069)

---

## 📄 License

MIT License — see [LICENSE](LICENSE).
