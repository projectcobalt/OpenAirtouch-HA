"""OpenAirTouch sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OpenAirTouchCoordinator, indexed
from .entity import OpenAirTouchEntity, ac_device_info, sensor_device_info, zone_device_info
from .state import ac_id_for_group, group_records, real_ac_ids, real_zone_ids, spill_group_ids, zone_id_for_sensor_row


@dataclass(frozen=True, kw_only=True)
class OpenAirTouchSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OpenAirTouchCoordinator = hass.data[DOMAIN][entry.entry_id]
    state = coordinator.data and ((coordinator.data.get("runtime") or {}).get("state") or {})
    entities: list[SensorEntity] = []

    for ac_id in real_ac_ids(state):
        entities.append(OpenAirTouchAcSensor(
            coordinator,
            ac_id,
            OpenAirTouchSensorDescription(
                key="error_code",
                name="Error Code",
                value_fn=lambda status: status.get("error_code"),
            ),
        ))

    for group_id in real_zone_ids(state):
        entities.append(OpenAirTouchZoneSensor(coordinator, group_id, OpenAirTouchSensorDescription(
            key="percentage",
            name="Damper",
            value_fn=lambda status: status.get("percentage"),
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        )))

    for group_id in sorted(spill_group_ids(state)):
        ac_id = ac_id_for_group(state, group_id)
        if ac_id is not None:
            entities.append(OpenAirTouchSpillDamperSensor(coordinator, group_id, ac_id))

    for row in state.get("sensor_view") or []:
        if not isinstance(row, dict) or "id" not in row:
            continue
        if row.get("kind") == "supply_air" and row.get("ac") not in real_ac_ids(state):
            continue
        sensor_id = str(row["id"])
        entities.append(OpenAirTouchSensorViewSensor(coordinator, sensor_id, OpenAirTouchSensorDescription(
            key="temperature",
            name="Temperature",
            value_fn=lambda sensor_row: sensor_row.get("temperature"),
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
        )))
        if row.get("battery") is not None:
            entities.append(OpenAirTouchSensorViewSensor(coordinator, sensor_id, OpenAirTouchSensorDescription(
                key="battery",
                name="Battery",
                value_fn=lambda sensor_row: sensor_row.get("battery"),
                device_class=SensorDeviceClass.BATTERY,
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
            )))
        if row.get("signal") is not None:
            entities.append(OpenAirTouchSensorViewSensor(coordinator, sensor_id, OpenAirTouchSensorDescription(
                key="signal",
                name="Signal",
                value_fn=lambda sensor_row: sensor_row.get("signal"),
                native_unit_of_measurement=PERCENTAGE,
                state_class=SensorStateClass.MEASUREMENT,
            )))

    async_add_entities(entities)


class OpenAirTouchAcSensor(OpenAirTouchEntity, SensorEntity):
    """Sensor for an AC record."""

    def __init__(self, coordinator: OpenAirTouchCoordinator, ac_id: int, description: OpenAirTouchSensorDescription) -> None:
        super().__init__(coordinator, f"ac_{ac_id + 1}_{description.key}")
        self.ac_id = ac_id
        self.entity_description = description
        self._attr_name = description.name
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class

    @property
    def native_value(self) -> Any:
        record = indexed(self._airtouch_state.get("acs") or {}, self.ac_id) or {}
        return self.entity_description.value_fn(record.get("status") or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        record = indexed(self._airtouch_state.get("acs") or {}, self.ac_id) or {}
        status = record.get("status") or {}
        base = record.get("base") or {}
        if self.entity_description.key != "error_code":
            return None
        return {
            "error_display": status.get("error_display"),
            "brand": base.get("brand"),
        }

    @property
    def device_info(self):
        record = indexed(self._airtouch_state.get("acs") or {}, self.ac_id) or {}
        base = record.get("base") or {}
        return ac_device_info(self.coordinator, self.ac_id, base.get("name"))


class OpenAirTouchZoneSensor(OpenAirTouchEntity, SensorEntity):
    """Sensor for a zone record."""

    def __init__(self, coordinator: OpenAirTouchCoordinator, group_id: int, description: OpenAirTouchSensorDescription) -> None:
        super().__init__(coordinator, f"zone_{group_id + 1}_{description.key}")
        self.group_id = group_id
        self.entity_description = description
        self._attr_name = description.name
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class

    @property
    def native_value(self) -> Any:
        groups = self._airtouch_state.get("active_groups") or self._airtouch_state.get("groups") or {}
        record = indexed(groups, self.group_id) or {}
        return self.entity_description.value_fn(record.get("status") or {})

    @property
    def device_info(self):
        groups = self._airtouch_state.get("active_groups") or self._airtouch_state.get("groups") or {}
        record = indexed(groups, self.group_id) or {}
        return zone_device_info(
            self.coordinator,
            self.group_id,
            ac_id=ac_id_for_group(self._airtouch_state, self.group_id),
            name=record.get("name") or f"Zone {self.group_id + 1}",
        )


class OpenAirTouchSpillDamperSensor(OpenAirTouchEntity, SensorEntity):
    """Read-only spill damper percentage attached to the owning AC device."""

    _attr_device_class = None
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: OpenAirTouchCoordinator, group_id: int, ac_id: int) -> None:
        super().__init__(coordinator, f"ac_{ac_id + 1}_spill_zone_{group_id + 1}_damper")
        self.group_id = group_id
        self.ac_id = ac_id
        self._attr_name = "Spill Damper"

    @property
    def name(self) -> str:
        return "Spill Damper"

    @property
    def native_value(self) -> Any:
        status = self._record.get("status") if self._record else {}
        return status.get("percentage")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        status = self._record.get("status") if self._record else {}
        return {
            "group": self.group_id,
            "ac": self.ac_id,
            "power_name": status.get("power_name"),
            "spill_on": status.get("spill_on"),
        }

    @property
    def device_info(self):
        record = indexed(self._airtouch_state.get("acs") or {}, self.ac_id) or {}
        base = record.get("base") or {}
        return ac_device_info(self.coordinator, self.ac_id, base.get("name"))

    @property
    def _record(self) -> dict[str, Any]:
        groups = self._airtouch_state.get("active_groups") or self._airtouch_state.get("groups") or {}
        return indexed(groups, self.group_id) or {}


class OpenAirTouchSensorViewSensor(OpenAirTouchEntity, SensorEntity):
    """Sensor for an RF, touchpad, or supply-air sensor view row."""

    def __init__(self, coordinator: OpenAirTouchCoordinator, sensor_id: str, description: OpenAirTouchSensorDescription) -> None:
        super().__init__(coordinator, f"sensor_{_safe_id(sensor_id)}_{description.key}")
        self.sensor_id = sensor_id
        self.entity_description = description
        self._attr_name = f"Sensor {sensor_id} {description.name}"
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class

    @property
    def name(self) -> str:
        row = self._row or {}
        if row.get("kind") == "supply_air":
            return f"Supply Air {self.entity_description.name}"
        if row.get("kind") == "touchpad":
            return f"{_display_name(row, self.sensor_id)} {self.entity_description.name}"
        return self.entity_description.name

    @property
    def device_info(self):
        row = self._row or {}
        if row.get("kind") == "supply_air":
            ac_id = row.get("ac")
            if isinstance(ac_id, int):
                record = indexed(self._airtouch_state.get("acs") or {}, ac_id) or {}
                base = record.get("base") or {}
                return ac_device_info(self.coordinator, ac_id, base.get("name"))
        if row.get("kind") == "touchpad":
            return super().device_info
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
    def native_value(self) -> Any:
        row = self._row
        return None if row is None else self.entity_description.value_fn(row)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        row = self._row
        if row is None:
            return {}
        return {
            "address": row.get("address"),
            "kind": row.get("kind"),
            "status": row.get("status"),
            "present": row.get("present"),
            "listed": row.get("listed"),
            "mapped_groups": row.get("mapped_groups"),
            "mac": row.get("mac"),
        }

    @property
    def _row(self) -> dict[str, Any] | None:
        for row in self._airtouch_state.get("sensor_view") or []:
            if isinstance(row, dict) and str(row.get("id")) == self.sensor_id:
                return row
        return None


def _safe_id(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_") or "unknown"


def _display_name(row: dict[str, Any], fallback: str) -> str:
    value = str(row.get("name") or fallback).replace("_", " ").strip()
    return " ".join(word.capitalize() for word in value.split()) or fallback
