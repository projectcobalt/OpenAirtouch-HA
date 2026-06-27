"""OpenAirTouch binary sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OpenAirTouchCoordinator
from .entity import OpenAirTouchEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OpenAirTouchCoordinator = hass.data[DOMAIN][entry.entry_id]
    state = coordinator.data and ((coordinator.data.get("runtime") or {}).get("state") or {})
    rows = state.get("sensor_view") or []
    entities = [
        OpenAirTouchLowBatterySensor(coordinator, int(row["id"]))
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("id"), int)
    ]
    async_add_entities(entities)


class OpenAirTouchLowBatterySensor(OpenAirTouchEntity, BinarySensorEntity):
    """Low battery sensor for an RF sensor row."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, coordinator: OpenAirTouchCoordinator, sensor_id: int) -> None:
        super().__init__(coordinator, f"sensor_{sensor_id}_low_battery")
        self.sensor_id = sensor_id
        self._attr_name = f"Sensor {sensor_id} Low Battery"

    @property
    def is_on(self) -> bool | None:
        for row in self._airtouch_state.get("sensor_view") or []:
            if isinstance(row, dict) and row.get("id") == self.sensor_id:
                value = row.get("low_battery")
                return None if value is None else bool(value)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        for row in self._airtouch_state.get("sensor_view") or []:
            if isinstance(row, dict) and row.get("id") == self.sensor_id:
                return {
                    "address": row.get("address"),
                    "kind": row.get("kind"),
                    "status": row.get("status"),
                    "mapped_groups": row.get("mapped_groups"),
                }
        return {}
