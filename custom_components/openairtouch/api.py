"""HTTP client for the OpenAirTouch add-on API."""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientError, ClientSession


class OpenAirTouchApiError(Exception):
    """Raised when the OpenAirTouch API cannot be reached or parsed."""


class OpenAirTouchClient:
    """Small async client for the OpenAirTouch add-on."""

    def __init__(self, session: ClientSession, base_url: str) -> None:
        self._session = session
        self.base_url = base_url.rstrip("/")

    async def health(self) -> dict[str, Any]:
        """Return add-on health."""
        return await self._get_json("/api/health")

    async def state(self) -> dict[str, Any]:
        """Return the full add-on state snapshot."""
        return await self._get_json("/api/state")

    async def events(self) -> dict[str, Any]:
        """Return recent add-on runtime events."""
        return await self._get_json("/api/events")

    async def command(self, action: str, data: dict[str, Any]) -> dict[str, Any]:
        """Send a command intent to the add-on."""
        return await self._post_json("/api/command", {"action": action, "data": data})

    async def _get_json(self, path: str) -> dict[str, Any]:
        try:
            async with asyncio.timeout(10):
                async with self._session.get(f"{self.base_url}{path}") as response:
                    response.raise_for_status()
                    payload = await response.json()
        except (TimeoutError, ClientError, ValueError) as exc:
            raise OpenAirTouchApiError(str(exc)) from exc
        if not isinstance(payload, dict):
            raise OpenAirTouchApiError("API response was not an object")
        return payload

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with asyncio.timeout(10):
                async with self._session.post(f"{self.base_url}{path}", json=payload) as response:
                    response.raise_for_status()
                    body = await response.json()
        except (TimeoutError, ClientError, ValueError) as exc:
            raise OpenAirTouchApiError(str(exc)) from exc
        if not isinstance(body, dict):
            raise OpenAirTouchApiError("API response was not an object")
        return body
