"""Config flow for OpenAirTouch."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OpenAirTouchApiError, OpenAirTouchClient
from .const import CONF_URL, DEFAULT_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _validate_url(hass: HomeAssistant, url: str) -> dict[str, Any]:
    client = OpenAirTouchClient(async_get_clientsession(hass), url)
    health = await client.health()
    if "status" not in health:
        raise OpenAirTouchApiError("missing status in health response")
    return health


class OpenAirTouchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an OpenAirTouch config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            url = str(user_input[CONF_URL]).rstrip("/")
            try:
                await _validate_url(self.hass, url)
            except OpenAirTouchApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating OpenAirTouch URL")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="OpenAirTouch", data={CONF_URL: url})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_URL, default=DEFAULT_URL): str}),
            errors=errors,
        )
