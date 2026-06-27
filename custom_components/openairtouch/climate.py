"""OpenAirTouch climate entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OpenAirTouchCoordinator, indexed
from .entity import OpenAirTouchEntity

AC_MODE_TO_HVAC = {
    0: HVACMode.AUTO,
    1: HVACMode.HEAT,
    2: HVACMode.DRY,
    3: HVACMode.FAN_ONLY,
    4: HVACMode.COOL,
}
HVAC_TO_AC_MODE = {value: key for key, value in AC_MODE_TO_HVAC.items()}
FAN_TO_NAME = {0: "auto", 1: "low", 2: "medium", 3: "high"}
NAME_TO_FAN = {value: key for key, value in FAN_TO_NAME.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OpenAirTouchCoordinator = hass.data[DOMAIN][entry.entry_id]
    state = coordinator.data and ((coordinator.data.get("runtime") or {}).get("state") or {})
    entities: list[ClimateEntity] = []

    for raw_id in sorted((state.get("acs") or {}), key=lambda item: int(item)):
        entities.append(OpenAirTouchAcClimate(coordinator, int(raw_id)))

    groups = state.get("active_groups") or state.get("groups") or {}
    for raw_id, group in sorted(groups.items(), key=lambda item: int(item[0])):
        status = (group or {}).get("status") or {}
        if status.get("has_sensor") is True:
            entities.append(OpenAirTouchZoneClimate(coordinator, int(raw_id)))

    async_add_entities(entities)


class OpenAirTouchAcClimate(OpenAirTouchEntity, ClimateEntity):
    """Climate entity for an AirTouch AC head."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.COOL,
    ]
    _attr_fan_modes = ["auto", "low", "medium", "high"]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

    def __init__(self, coordinator: OpenAirTouchCoordinator, ac_id: int) -> None:
        super().__init__(coordinator, f"ac_{ac_id + 1}_climate")
        self.ac_id = ac_id
        self._attr_name = f"AC {ac_id + 1}"

    @property
    def _record(self) -> dict[str, Any]:
        return indexed(self._airtouch_state.get("acs") or {}, self.ac_id) or {}

    @property
    def name(self) -> str:
        base = self._record.get("base") or {}
        return base.get("name") or self._attr_name

    @property
    def min_temp(self) -> float:
        settings = self._record.get("settings") or {}
        return float(settings.get("min_setpoint") or 16)

    @property
    def max_temp(self) -> float:
        settings = self._record.get("settings") or {}
        return float(settings.get("max_setpoint") or 30)

    @property
    def current_temperature(self) -> float | None:
        status = self._record.get("status") or {}
        return _float_or_none(status.get("sensor_temp") or status.get("temperature") or status.get("current_temp"))

    @property
    def target_temperature(self) -> float | None:
        status = self._record.get("status") or {}
        return _float_or_none(status.get("setpoint"))

    @property
    def hvac_mode(self) -> HVACMode | None:
        status = self._record.get("status") or {}
        if status.get("power_on") is False:
            return HVACMode.OFF
        return AC_MODE_TO_HVAC.get(status.get("mode"), HVACMode.AUTO)

    @property
    def fan_mode(self) -> str | None:
        status = self._record.get("status") or {}
        return FAN_TO_NAME.get(status.get("fan"))

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.coordinator.client.command("ac_status", {"ac": self.ac_id, "setpoint": int(round(float(temperature)))})
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            payload: dict[str, Any] = {"ac": self.ac_id, "power_on": False}
        else:
            payload = {"ac": self.ac_id, "power_on": True}
            if hvac_mode in HVAC_TO_AC_MODE:
                payload["mode"] = HVAC_TO_AC_MODE[hvac_mode]
        await self.coordinator.client.command("ac_status", payload)
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if fan_mode not in NAME_TO_FAN:
            return
        await self.coordinator.client.command("ac_status", {"ac": self.ac_id, "fan": NAME_TO_FAN[fan_mode]})
        await self.coordinator.async_request_refresh()


class OpenAirTouchZoneClimate(OpenAirTouchEntity, ClimateEntity):
    """Climate entity for a sensor-backed AirTouch zone."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, coordinator: OpenAirTouchCoordinator, group_id: int) -> None:
        super().__init__(coordinator, f"zone_{group_id + 1}_climate")
        self.group_id = group_id
        self._attr_name = f"Zone {group_id + 1}"

    @property
    def _record(self) -> dict[str, Any]:
        groups = self._airtouch_state.get("active_groups") or self._airtouch_state.get("groups") or {}
        return indexed(groups, self.group_id) or {}

    @property
    def name(self) -> str:
        return self._record.get("name") or self._attr_name

    @property
    def min_temp(self) -> float:
        ac = _ac_for_group(self._airtouch_state, self.group_id)
        settings = (ac or {}).get("settings") or {}
        return float(settings.get("min_setpoint") or 16)

    @property
    def max_temp(self) -> float:
        ac = _ac_for_group(self._airtouch_state, self.group_id)
        settings = (ac or {}).get("settings") or {}
        return float(settings.get("max_setpoint") or 30)

    @property
    def current_temperature(self) -> float | None:
        status = self._record.get("status") or {}
        return _float_or_none(status.get("temperature"))

    @property
    def target_temperature(self) -> float | None:
        status = self._record.get("status") or {}
        return _float_or_none(status.get("setpoint"))

    @property
    def hvac_mode(self) -> HVACMode | None:
        status = self._record.get("status") or {}
        return HVACMode.HEAT_COOL if status.get("power_name") in {"on", "turbo"} else HVACMode.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.coordinator.client.command("group_setpoint", {"group": self.group_id, "setpoint": int(round(float(temperature)))})
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        current_setpoint = self.target_temperature
        payload: dict[str, Any] = {
            "group": self.group_id,
            "on": hvac_mode != HVACMode.OFF,
            "sensor_control": True,
        }
        if current_setpoint is not None:
            payload["setpoint"] = int(round(current_setpoint))
        await self.coordinator.client.command("group_power", payload)
        await self.coordinator.async_request_refresh()


def _float_or_none(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _ac_for_group(state: dict[str, Any], group_id: int) -> dict[str, Any] | None:
    for raw_ac, record in (state.get("acs") or {}).items():
        base = (record or {}).get("base") or {}
        start = base.get("group_start")
        count = base.get("group_count")
        if isinstance(start, int) and isinstance(count, int) and start <= group_id < start + count:
            return record
    acs = state.get("acs") or {}
    if len(acs) == 1:
        return next(iter(acs.values()))
    return None
