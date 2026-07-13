# 🚀 PyTradoWix

<p align="center">
  <strong>Unofficial Python API Wrapper & client for the TradoWix binary options trading platform.</strong>
</p>
<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue" alt="Python Versions"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/typing-strict-purple" alt="Typing"/>
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Type Coverage"/>
</p>

---

## 📘 About

**pytradowix** is a high-performance, asynchronous Python client wrapper designed for the [TradoWix](https://tradowix.com) trading platform. Engineered for **algorithmic trading**, **automated signal execution**, and **financial market data analysis**, it enables seamless integration with TradoWix's WebSocket and REST APIs.

### 🌟 Key Features

*   **⚡ Real-Time Price Streaming**: Fast, asynchronous subscription to live currency and OTC asset price tick updates.
*   **📈 Unlimited Historical Data**: Retrieve comprehensive historical candles (OHLC) using backward-paginated queries (tested for weeks/months of history).
*   **🤖 Automated Trade Execution**: Place binary option orders (CALL/PUT) programmatically and await resolution results.
*   **🔒 Secure Session Caching**: Automatic session token caching (`~/.pytradowix/session.json`) to bypass repeated credentials requests.
*   **🔄 Connection Recovery**: In-built automatic reconnection policy with custom exponential backoff delays.
*   **🛡️ Fully Type-Safe**: Complies with strict type-checking (`mypy --strict`) and exports fully documented frozen dataclasses.

---

## 📌 Table of Contents
*   [🛠 Installation](#-installation)
*   [⚡ Quick Start](#-quick-start)
*   [🔔 Event Callbacks](#-event-callbacks)
*   [💡 API Reference](#-api-reference)
*   [📦 Typed Data Classes](#-typed-data-classes)
*   [🔄 Auto-Reconnect](#-auto-reconnect)
*   [🔒 Session Caching](#-session-caching)
*   [🧪 Running Tests](#-running-tests)
*   [📁 Project Structure](#-project-structure)
*   [⚙️ Environment Variables](#%EF%B8%8F-environment-variables)
*   [💬 Contact](#-contact)
*   [📄 License](#-license)

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

## 🔔 Event Callbacks

The client supports both synchronous and asynchronous event callbacks to respond to real-time events on the platform:

```python
# Triggered when the WebSocket connection is successfully authenticated and instruments cache is loaded
client.on_connect = lambda: print("🚀 Connected and ready!")

# Triggered when the connection closes gracefully or unexpectedly
client.on_disconnect = lambda: print("🔌 Disconnected!")

# Triggered whenever the account balance changes (e.g. from trade placements or settlements)
client.on_balance_update = lambda balance: print(f"💰 New Balance: {balance.current_balance} {balance.currency}")

# Triggered automatically when any placed trade is settled by the server
client.on_trade_settled = lambda result: print(f"Settled: {result.trade_id} -> {result.result.upper()} (${result.profit:+.2f})")
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
| `is_asset_tradable(symbol)` | Safety check verifying if an asset is active and open for trading |
| `change_account(mode)` | Switch between `"demo"` and `"real"` account modes |
| `edit_demo_balance(amount)` | Request a demo balance top-up |
| `get_highest_payout_assets(min_payout, mode)` | Filter active/open instruments by minimum payout rate, sorted in descending order of payout |
| `subscribe_ticks(symbol)` | Start receiving live `Quote` ticks for a symbol |
| `unsubscribe_ticks(symbol)` | Stop receiving ticks for a symbol |
| `get_candles(symbol, end_from_time, minutes, timeframe)` | Fetch a single batch of historical candles |
| `get_historical_candles(symbol, amount_of_seconds, period)` | Fetch unlimited history via backward pagination |
| `buy(amount, symbol, direction, duration, is_demo, expiration_mode)` | Place a turbo (minutes) or blitz (seconds) trade |
| `put(amount, symbol, duration)` | Convenience alias for `buy(..., direction="put")` |
| `buy_blitz(amount, symbol, duration_seconds)` | Place a blitz call (seconds) trade |
| `put_blitz(amount, symbol, duration_seconds)` | Place a blitz put (seconds) trade |
| `check_win(trade_id, timeout)` | Wait for and return a `TradeResult` |
| `get_open_trades(is_demo, timeout)` | Returns `list[TradeResult]` — retrieve all active open trades |
| `get_trade_history(page, page_size, is_demo, timeout)` | Returns `list[TradeResult]` — retrieve historical settled trades |
| `get_server_time()` | Returns the estimated synchronized server timestamp in seconds |

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
