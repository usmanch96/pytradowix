"""Public, immutable dataclasses for the pytradowix API surface.

These types are returned by public methods so consumers get real IDE
completion and mypy coverage instead of opaque dict[str, Any].
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Optional

# -- Aliases ------------------------------------------------------------------

TradeStatus = Literal["win", "loss", "draw", "pending"]
TradeDirection = Literal["call", "put"]


# -- Candle -------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class Candle:
    """A single OHLC candle. Times are unix-epoch seconds."""

    time: int
    open: float
    high: float
    low: float
    close: float

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Candle":
        return cls(
            time=int(data.get("time", 0)),
            open=float(data.get("open", 0.0)),
            high=float(data.get("high", 0.0)),
            low=float(data.get("low", 0.0)),
            close=float(data.get("close", 0.0)),
        )

    @classmethod
    def from_array(cls, arr: list[Any]) -> "Candle":
        """Build from broker's raw array: [timestamp_ms, open, high, low, close]."""
        if len(arr) < 5:
            raise ValueError(f"candle array too short: {arr!r}")
        return cls(
            time=int(arr[0] / 1000),
            open=float(arr[1]),
            high=float(arr[2]),
            low=float(arr[3]),
            close=float(arr[4]),
        )

    @property
    def color(self) -> Literal["green", "red", "doji"]:
        if self.close > self.open:
            return "green"
        if self.close < self.open:
            return "red"
        return "doji"


# -- Balance ------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class Balance:
    """A snapshot of account balances."""

    demo_balance: float
    real_balance: float
    bonus_balance: float
    current_balance: float
    currency: str
    is_demo: bool

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], is_demo: bool = True) -> "Balance":
        return cls(
            demo_balance=float(data.get("demoBalance", 0.0)),
            real_balance=float(data.get("realBalance", 0.0)),
            bonus_balance=float(data.get("bonusBalance", 0.0)),
            current_balance=float(data.get("currentBalance", 0.0)),
            currency=str(data.get("currency", "USD")),
            is_demo=is_demo,
        )


# -- ProfileInfo --------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class ProfileInfo:
    """User profile information."""

    id: Optional[str]
    trader_id: Optional[int]
    email: Optional[str]
    full_name: Optional[str]
    display_name: Optional[str]
    phone: Optional[str] = None
    country: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProfileInfo":
        return cls(
            id=data.get("id"),
            trader_id=data.get("traderId"),
            email=data.get("email"),
            full_name=data.get("fullName"),
            display_name=data.get("displayName"),
            phone=data.get("phone"),
            country=data.get("country"),
            date_of_birth=data.get("dateOfBirth"),
            address=data.get("address"),
            city=data.get("city"),
            postal_code=data.get("postalCode"),
        )


# -- AssetInfo ----------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class AssetInfo:
    """Asset descriptor returned by get_assets()."""

    id: str
    symbol: str
    name: str
    display_name: str
    category: str
    group_name: str
    precision: int
    is_active: bool
    is_otc: bool
    turbo_payout_rate: float
    blitz_payout_rate: float
    is_open: bool

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AssetInfo":
        return cls(
            id=str(data.get("id", "")),
            symbol=str(data.get("symbol", "")),
            name=str(data.get("name", "")),
            display_name=str(data.get("displayName", data.get("name", ""))),
            category=str(data.get("category", "")),
            group_name=str(data.get("groupName", "")),
            precision=int(data.get("precision", 5)),
            is_active=bool(data.get("isActive", True)),
            is_otc=bool(data.get("isOtc", False)),
            turbo_payout_rate=float(data.get("turboPayout", 0.0)),
            blitz_payout_rate=float(data.get("blitzPayout", 0.0)),
            is_open=bool(data.get("isOpen", True)),
        )


# -- TradeResult --------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class TradeResult:
    """Outcome of a completed trade settlement."""

    trade_id: str
    user_id: str
    symbol: str
    direction: str
    amount: float
    open_price: float
    close_price: float
    result: str
    profit: float
    new_balance: float
    open_time: str
    expiry_time: str
    close_time: str
    duration: int
    is_demo: bool

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TradeResult":
        result_raw = str(data.get("result", "")).lower()
        status = result_raw if result_raw in ("win", "loss", "draw") else "pending"
        return cls(
            trade_id=str(data.get("tradeId", "")),
            user_id=str(data.get("userId", "")),
            symbol=str(data.get("symbol", "")),
            direction=str(data.get("direction", "")),
            amount=float(data.get("amount", 0.0)),
            open_price=float(data.get("openPrice", 0.0)),
            close_price=float(data.get("closePrice", 0.0)),
            result=status,
            profit=float(data.get("profit", 0.0)),
            new_balance=float(data.get("newBalance", 0.0)),
            open_time=str(data.get("openTime", "")),
            expiry_time=str(data.get("expiryTime", "")),
            close_time=str(data.get("closeTime", "")),
            duration=int(data.get("duration", 0)),
            is_demo=bool(data.get("isDemo", True)),
        )


# -- Quote --------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class Quote:
    """A single real-time price tick."""

    symbol: str
    price: float
    timestamp: float  # unix seconds


# -- ReconnectPolicy ----------------------------------------------------------

@dataclass(slots=True)
class ReconnectPolicy:
    """Configures auto-reconnect behaviour for the Tradowix client."""

    enabled: bool = True
    max_attempts: int = 0
    base_delay: float = 1.0
    max_delay: float = 30.0


__all__ = [
    "AssetInfo",
    "Balance",
    "Candle",
    "ProfileInfo",
    "Quote",
    "ReconnectPolicy",
    "TradeDirection",
    "TradeResult",
    "TradeStatus",
]

