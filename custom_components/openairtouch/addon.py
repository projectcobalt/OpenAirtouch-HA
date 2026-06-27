"""Provide OpenAirTouch add-on helpers."""

from __future__ import annotations

import logging

from homeassistant.components.hassio import AddonManager
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(DOMAIN)


def get_addon_manager(hass: HomeAssistant, slug: str) -> AddonManager:
    """Return a Supervisor add-on manager for an installed OpenAirTouch add-on."""
    return AddonManager(hass, _LOGGER, "OpenAirTouch", slug)
