"""OpenAirTouch binary sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OpenAirTouchCoordinator, indexed
from .entity import OpenAirTouchEntity, sensor_device_info, zone_device_info
from .state import ac_id_for_group, zone_id_for_sensor_row


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OpenAirTouchCoordinator = hass.data[DOMAIN][entry.entry_id]
    state = coordinator.data and ((coordinator.data.get("runtime") or {}).get("state") or {})
    rows = state.get("sensor_view") or []
    entities = [
        OpenAirTouchLowBatterySensor(coordinator, str(row["id"]))
        for row in rows
        if isinstance(row, dict) and row.get("low_battery") is not None
    ]
    async_add_entities(entities)


class OpenAirTouchLowBatterySensor(OpenAirTouchEntity, BinarySensorEntity):
    """Low battery sensor for an RF sensor row."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, coordinator: OpenAirTouchCoordinator, sensor_id: str) -> None:
        super().__init__(coordinator, f"sensor_{_safe_id(sensor_id)}_low_battery")
        self.sensor_id = sensor_id
        self._attr_name = "Low Battery"

    @property
    def is_on(self) -> bool | None:
        for row in self._airtouch_state.get("sensor_view") or []:
            if isinstance(row, dict) and str(row.get("id")) == self.sensor_id:
                value = row.get("low_battery")
                return None if value is None else bool(value)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        for row in self._airtouch_state.get("sensor_view") or []:
            if isinstance(row, dict) and str(row.get("id")) == self.sensor_id:
                return {
                    "address": row.get("address"),
                    "kind": row.get("kind"),
                    "status": row.get("status"),
                    "mapped_groups": row.get("mapped_groups"),
                }
        return {}

    @property
    def device_info(self):
        row = self._row or {}
        zone_id = zone_id_for_sensor_row(self._airtouch_state, row)
        if zone_id is not None:
            groups = self._airtouch_state.get("active_groups") or self._airtouch_state.get("groups") or {}
            record = indexed(groups, zone_id) or {}
            return zone_device_info(
                self.coordinator,
                zone_id,
                ac_id=ac_id_for_group(self._airtouch_state, zone_id),
                name=record.get("name") or f"Zone {zone_id + 1}",
            )
        return sensor_device_info(
            self.coordinator,
            self.sensor_id,
            kind=row.get("kind"),
            name=row.get("name"),
        )

    @property
    def _row(self) -> dict[str, Any] | None:
        for row in self._airtouch_state.get("sensor_view") or []:
            if isinstance(row, dict) and str(row.get("id")) == self.sensor_id:
                return row
        return None


def _safe_id(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_") or "unknown"
