"""OpenAirTouch zone damper covers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import CoverDeviceClass, CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import OpenAirTouchCoordinator, indexed
from .entity import OpenAirTouchEntity, zone_device_info
from .state import ac_id_for_group, real_zone_ids


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OpenAirTouchCoordinator = hass.data[DOMAIN][entry.entry_id]
    state = coordinator.data and ((coordinator.data.get("runtime") or {}).get("state") or {})
    async_add_entities(OpenAirTouchZoneDamper(coordinator, group_id) for group_id in real_zone_ids(state))


class OpenAirTouchZoneDamper(OpenAirTouchEntity, CoverEntity):
    """Cover entity for a zone damper percentage."""

    _attr_device_class = CoverDeviceClass.DAMPER
    _attr_supported_features = CoverEntityFeature.SET_POSITION | CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, coordinator: OpenAirTouchCoordinator, group_id: int) -> None:
        super().__init__(coordinator, f"zone_{group_id + 1}_damper")
        self.group_id = group_id
        self._attr_name = f"Zone {group_id + 1} Damper"

    @property
    def _record(self) -> dict[str, Any]:
        groups = self._airtouch_state.get("active_groups") or self._airtouch_state.get("groups") or {}
        return indexed(groups, self.group_id) or {}

    @property
    def name(self) -> str:
        return f"{self._record.get('name') or f'Zone {self.group_id + 1}'} Damper"

    @property
    def device_info(self):
        return zone_device_info(
            self.coordinator,
            self.group_id,
            ac_id=ac_id_for_group(self._airtouch_state, self.group_id),
            name=self._record.get("name") or f"Zone {self.group_id + 1}",
        )

    @property
    def current_cover_position(self) -> int | None:
        status = self._record.get("status") or {}
        value = status.get("percentage")
        try:
            return None if value is None else max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return None

    @property
    def is_closed(self) -> bool | None:
        position = self.current_cover_position
        return None if position is None else position == 0

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = int(kwargs["position"])
        await self.coordinator.client.command("group_percentage", {"group": self.group_id, "percentage": position})
        await self.coordinator.async_request_refresh()

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.async_set_cover_position(position=100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.async_set_cover_position(position=0)
