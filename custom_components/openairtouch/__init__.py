"""OpenAirTouch Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OpenAirTouchClient
from .const import CONF_INSTANCE_ID, CONF_URL, DOMAIN, PLATFORMS
from .coordinator import OpenAirTouchCoordinator
from .registry import async_migrate_registry_entries, instance_id_for_entry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenAirTouch from a config entry."""
    instance_id = instance_id_for_entry(entry)
    if entry.data.get(CONF_INSTANCE_ID) != instance_id:
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_INSTANCE_ID: instance_id})

    client = OpenAirTouchClient(async_get_clientsession(hass), entry.data[CONF_URL])
    coordinator = OpenAirTouchCoordinator(hass, client, instance_id)
    await coordinator.async_config_entry_first_refresh()

    state = (coordinator.data.get("runtime") or {}).get("state") or {}
    if isinstance(state, dict):
        await async_migrate_registry_entries(hass, entry, instance_id, state)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an OpenAirTouch config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        domain_data = hass.data.get(DOMAIN, {})
        domain_data.pop(entry.entry_id, None)
        if not domain_data:
            hass.data.pop(DOMAIN, None)
    return unloaded
