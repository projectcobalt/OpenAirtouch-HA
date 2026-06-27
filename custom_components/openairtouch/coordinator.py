"""Coordinator for OpenAirTouch runtime state."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OpenAirTouchApiError, OpenAirTouchClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class OpenAirTouchCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch OpenAirTouch state for all platforms."""

    def __init__(self, hass: HomeAssistant, client: OpenAirTouchClient, instance_id: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
        )
        self.client = client
        self.instance_id = instance_id

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.state()
        except OpenAirTouchApiError as exc:
            raise UpdateFailed(str(exc)) from exc


def runtime_state(data: dict[str, Any] | None) -> dict[str, Any]:
    """Return the normalized AirTouch runtime state from a coordinator payload."""
    runtime = (data or {}).get("runtime") or {}
    state = runtime.get("state") or {}
    return state if isinstance(state, dict) else {}


def indexed(mapping: Any, key: int) -> Any:
    """Read an integer-keyed API mapping after JSON converted keys to strings."""
    if not isinstance(mapping, dict):
        return None
    return mapping.get(key) if key in mapping else mapping.get(str(key))
