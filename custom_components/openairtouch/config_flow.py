"""Config flow for OpenAirTouch."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from aiohasupervisor import SupervisorError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.hassio import AddonError
from homeassistant.components.hassio.const import DOMAIN as HASSIO_DOMAIN
from homeassistant.components.hassio.handler import get_supervisor_client
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.hassio import is_hassio

from .addon import get_addon_manager
from .api import OpenAirTouchApiError, OpenAirTouchClient
from .const import CONF_URL, DEFAULT_URL, DOMAIN
from .discovery import (
    addon_slug_from_hassio_info,
    hassio_discovery_unique_id,
    is_openairtouch_hassio_discovery,
    normalise_url,
    url_from_hassio_discovery,
)

_LOGGER = logging.getLogger(__name__)


async def _validate_url(hass: HomeAssistant, url: str) -> dict[str, Any]:
    client = OpenAirTouchClient(async_get_clientsession(hass), url)
    health = await client.health()
    if "status" not in health:
        raise OpenAirTouchApiError("missing status in health response")
    return health


async def _async_discovered_hassio_urls(hass: HomeAssistant) -> list[tuple[str, str]]:
    """Return Supervisor-discovered OpenAirTouch URLs and unique IDs."""
    if not is_hassio(hass):
        return []

    results: list[tuple[str, str]] = []
    try:
        discoveries = await get_supervisor_client(hass).discovery.list()
    except SupervisorError as err:
        _LOGGER.debug("Unable to read Supervisor discovery info: %s", err)
    else:
        results.extend(await _async_hassio_urls_from_payloads(hass, discoveries))

    if not results:
        results.extend(await _async_installed_hassio_addon_urls(hass))
    return results


async def _async_installed_hassio_addon_urls(hass: HomeAssistant) -> list[tuple[str, str]]:
    """Return OpenAirTouch URLs from installed Supervisor add-on metadata."""
    addons = await _async_supervisor_data(hass, "/addons")
    addons_list = addons.get("addons") if isinstance(addons, dict) else None
    if not isinstance(addons_list, list):
        return []

    results: list[tuple[str, str]] = []
    for addon in addons_list:
        if not isinstance(addon, dict) or not is_openairtouch_hassio_discovery(addon):
            continue

        if result := await _async_hassio_url_from_payload(hass, addon):
            results.append(result)
    return results


async def _async_supervisor_data(hass: HomeAssistant, command: str) -> Any:
    """Return data from the Home Assistant Supervisor API."""
    hassio = hass.data.get(HASSIO_DOMAIN)
    if hassio is None:
        return None

    try:
        response = await hassio.send_command(command, method="get", source=f"{DOMAIN}.config_flow")
    except Exception as err:
        _LOGGER.debug("Unable to read Supervisor data from %s: %s", command, err)
        return None

    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


async def _async_hassio_urls_from_payloads(
    hass: HomeAssistant, payloads: list[Any]
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for discovery_info in payloads:
        if not is_openairtouch_hassio_discovery(discovery_info):
            continue
        if result := await _async_hassio_url_from_payload(hass, discovery_info):
            results.append(result)
    return results


async def _async_hassio_url_from_payload(
    hass: HomeAssistant, discovery_info: Any
) -> tuple[str, str] | None:
    """Return an add-on URL from Matter-style Supervisor discovery helpers."""
    if slug := addon_slug_from_hassio_info(discovery_info):
        try:
            addon_discovery_info = await get_addon_manager(
                hass, slug
            ).async_get_addon_discovery_info()
        except AddonError as err:
            _LOGGER.debug("Unable to read OpenAirTouch add-on discovery info: %s", err)
        else:
            if isinstance(addon_discovery_info, dict):
                payload = {"slug": slug, "uuid": slug, **addon_discovery_info}
                if url := url_from_hassio_discovery(payload):
                    return (url, hassio_discovery_unique_id(payload, url))

    if url := url_from_hassio_discovery(discovery_info):
        return (url, hassio_discovery_unique_id(discovery_info, url))
    return None


class OpenAirTouchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an OpenAirTouch config flow."""

    VERSION = 1

    async def _async_create_entry_from_url(self, url: str, *, unique_id: str | None = None):
        """Validate an OpenAirTouch URL and create a config entry."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        url = normalise_url(url)
        if not _is_valid_url(url):
            raise OpenAirTouchApiError("invalid URL")
        await _validate_url(self.hass, url)
        await self.async_set_unique_id(unique_id or url)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="OpenAirTouch", data={CONF_URL: url})

    async def async_step_hassio(self, discovery_info: dict[str, Any]):
        """Handle discovery from the OpenAirTouch Home Assistant add-on."""
        if not is_openairtouch_hassio_discovery(discovery_info):
            return self.async_abort(reason="not_openairtouch_addon")

        url = url_from_hassio_discovery(discovery_info)
        if url is None:
            _LOGGER.warning("OpenAirTouch discovery did not include a routable add-on URL: %s", discovery_info)
            return self.async_abort(reason="missing_url")
        try:
            return await self._async_create_entry_from_url(
                url,
                unique_id=hassio_discovery_unique_id(discovery_info, url),
            )
        except OpenAirTouchApiError:
            _LOGGER.warning("Discovered OpenAirTouch add-on was not reachable")
            return self.async_abort(reason="cannot_connect")
        except Exception:
            _LOGGER.exception("Unexpected error setting up discovered OpenAirTouch add-on")
            return self.async_abort(reason="unknown")

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is None:
            for url, unique_id in await _async_discovered_hassio_urls(self.hass):
                try:
                    return await self._async_create_entry_from_url(url, unique_id=unique_id)
                except OpenAirTouchApiError:
                    _LOGGER.warning("Discovered OpenAirTouch add-on was not reachable")
                except Exception:
                    _LOGGER.exception("Unexpected error validating discovered OpenAirTouch add-on")

        if user_input is not None:
            try:
                return await self._async_create_entry_from_url(str(user_input[CONF_URL]))
            except OpenAirTouchApiError:
                errors["base"] = "invalid_url" if not _is_valid_url(str(user_input[CONF_URL])) else "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating OpenAirTouch URL")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_URL, default=DEFAULT_URL): str}),
            errors=errors,
        )


def _is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
