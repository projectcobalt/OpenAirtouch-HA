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
from .entity import OpenAirTouchEntity
from .state import real_ac_ids


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

    groups = state.get("active_groups") or state.get("groups") or {}
    for raw_id in sorted(groups, key=lambda item: int(item)):
        group_id = int(raw_id)
        entities.append(OpenAirTouchZoneSensor(coordinator, group_id, OpenAirTouchSensorDescription(
            key="temperature",
            name="Temperature",
            value_fn=lambda status: status.get("temperature"),
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
        )))
        entities.append(OpenAirTouchZoneSensor(coordinator, group_id, OpenAirTouchSensorDescription(
            key="percentage",
            name="Damper",
            value_fn=lambda status: status.get("percentage"),
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        )))

    for row in state.get("sensor_view") or []:
        if not isinstance(row, dict) or "id" not in row:
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
        self._attr_name = f"AC {ac_id + 1} {description.name}"
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


class OpenAirTouchZoneSensor(OpenAirTouchEntity, SensorEntity):
    """Sensor for a zone record."""

    def __init__(self, coordinator: OpenAirTouchCoordinator, group_id: int, description: OpenAirTouchSensorDescription) -> None:
        super().__init__(coordinator, f"zone_{group_id + 1}_{description.key}")
        self.group_id = group_id
        self.entity_description = description
        self._attr_name = f"Zone {group_id + 1} {description.name}"
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class

    @property
    def native_value(self) -> Any:
        groups = self._airtouch_state.get("active_groups") or self._airtouch_state.get("groups") or {}
        record = indexed(groups, self.group_id) or {}
        return self.entity_description.value_fn(record.get("status") or {})


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
        row = self._row
        label = row.get("name") if row else None
        return f"{label or f'Sensor {self.sensor_id}'} {self.entity_description.name}"

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
