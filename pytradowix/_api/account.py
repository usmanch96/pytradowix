"""Account-related methods for the Tradowix client.

This mixin is composed into Tradowix via multiple inheritance and relies
on attributes set up in Tradowix.__init__ inside pytradowix/client.py.
"""
from __future__ import annotations

import httpx
import logging
from typing import Optional

from pytradowix._base import _ClientBase
from pytradowix.exceptions import TradowixAuthError, TradowixException
from pytradowix.types import ProfileInfo, Balance, AssetInfo

logger = logging.getLogger(__name__)


class AccountMixin(_ClientBase):
    """Account connection, profile, balance, and session management."""

    async def connect(self) -> bool:
        """Connect to TradoWix via cached session or fresh credential login.

        Uses a cached ``session.json`` token if valid; falls back to a
        credentials POST and updates the cache on success.

        Returns:
            bool: ``True`` on successful connection.

        Raises:
            TradowixAuthError: On invalid credentials.
            TradowixException: On any other connection failure.
        """
        cached_token = self._session_token
        # Clean up any existing connection
        await self.close()
        self._session_token = cached_token

        from pytradowix.config import update_session

        self._session = httpx.AsyncClient(timeout=30.0)

        # Try utilizing cached session token if available
        if self._session_token:
            logger.info("Attempting to connect with cached session token...")
            try:
                self._session.cookies.set("session-token", self._session_token)
                profile_url = f"{self._base_url}/api/auth/profile"
                prof_resp = await self._session.get(profile_url)
                if prof_resp.status_code == 200:
                    self._profile_data = prof_resp.json()
                    await self._start_ws()
                    logger.info("Connected successfully using cached session token!")
                    return True
                else:
                    logger.info(
                        f"Cached session returned status {prof_resp.status_code}. Re-authenticating..."
                    )
            except Exception as e:
                logger.info(f"Cached session failed: {e}. Re-authenticating...")
                self._session_token = None
                await self._stop_ws()
                if self._session is not None:
                    await self._session.aclose()
                self._session = httpx.AsyncClient(timeout=30.0)

        # Fallback to standard credential login
        login_url = f"{self._base_url}/api/auth/login"
        payload = {"email": self._email, "password": self._password}

        logger.info("Logging in to TradoWix via credentials POST...")
        try:
            resp = await self._session.post(login_url, json=payload)
            if resp.status_code != 200:
                raise TradowixAuthError(
                    f"HTTP login failed with status {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            if not data.get("success"):
                raise TradowixAuthError(
                    f"Login response indicates failure: {data.get('message')}"
                )

            self._session_token = data.get("sessionToken")
            if not self._session_token:
                raise TradowixAuthError("Login response missing sessionToken")

            # Persist the newly acquired session token
            update_session(self._email, self._session_token, self._user_agent)

            self._session.cookies.set("session-token", self._session_token)

            # Fetch profile
            profile_url = f"{self._base_url}/api/auth/profile"
            prof_resp = await self._session.get(profile_url)
            if prof_resp.status_code == 200:
                self._profile_data = prof_resp.json()

            await self._start_ws()
            return True

        except Exception as e:
            logger.error(f"Failed to connect to TradoWix: {e}")
            await self.close()
            if isinstance(e, TradowixException):
                raise
            raise TradowixException(f"Connection failed: {e}") from e

    async def close(self) -> None:
        """Gracefully close the WebSocket and HTTP session."""
        await self._stop_ws()
        if self._session is not None:
            await self._session.aclose()
            self._session = None
        self._session_token = None
        self._profile_data = None

    async def change_account(self, mode: str) -> bool:
        """Switch between demo and real account mode.

        Since TradoWix binds ``isDemo`` at trade placement time rather than
        at the connection level, this simply updates the client's default
        flag so all subsequent ``buy()`` calls use the new mode.

        Args:
            mode: ``"demo"`` or ``"real"`` (case-insensitive).

        Returns:
            bool: ``True`` when the mode was successfully set.

        Raises:
            ValueError: If *mode* is not ``"demo"`` or ``"real"``.
        """
        mode_lower = mode.strip().lower()
        if mode_lower == "demo":
            self._is_demo = True
        elif mode_lower in ("real", "live"):
            self._is_demo = False
        else:
            raise ValueError(
                f"Invalid account mode '{mode}'. Use 'demo' or 'real'."
            )
        logger.info(f"Account mode switched to {'demo' if self._is_demo else 'real'}.")
        return True

    async def edit_demo_balance(self, amount: float = 10000.0) -> bool:
        """Request a demo balance top-up via the REST API.

        Args:
            amount: Target demo balance amount (default: 10,000).

        Returns:
            bool: ``True`` if the server accepted the request.

        Raises:
            TradowixException: If not connected or the request fails.
        """
        if not self._session:
            raise TradowixException("Not connected. Call connect() first.")

        url = f"{self._base_url}/api/account/demo/reset"
        try:
            resp = await self._session.post(url, json={"amount": amount})
            if resp.status_code == 200:
                logger.info(f"Demo balance reset requested to {amount}")
                return True
            logger.warning(
                f"Demo balance reset returned status {resp.status_code}: {resp.text}"
            )
            return False
        except Exception as e:
            raise TradowixException(f"edit_demo_balance failed: {e}") from e

    def get_profile(self) -> Optional[ProfileInfo]:
        """Return the current user profile from the connection cache.

        Returns:
            ProfileInfo: Typed profile object, or ``None`` if not connected.
        """
        if not self._profile_data:
            return None
        return ProfileInfo.from_dict(self._profile_data)

    def get_balance(self) -> Optional[Balance]:
        """Return the current account balance from the WebSocket cache.

        Returns:
            Balance: Typed balance object, or ``None`` if not yet received.
        """
        if not self._balance_data:
            return None
        return Balance.from_dict(self._balance_data, is_demo=self._is_demo)

    def get_assets(self) -> list[AssetInfo]:
        """Return all instruments as typed :class:`AssetInfo` objects.

        The list is populated automatically after ``connect()`` via the
        ``instruments`` WebSocket frame.

        Returns:
            list[AssetInfo]: Known tradeable instruments.
        """
        return [AssetInfo.from_dict(inst) for inst in self.instruments]

    def is_asset_tradable(self, symbol: str) -> bool:
        """Check if an asset is active and open for trading.

        Args:
            symbol: Asset symbol (e.g. ``"USDJPY-OTC"``).

        Returns:
            bool: ``True`` if the asset is active and open, ``False`` otherwise.
        """
        for asset in self.get_assets():
            if asset.symbol == symbol:
                return asset.is_active and asset.is_open
        return False

