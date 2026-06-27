"""Shared entity helpers for OpenAirTouch."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER, MODEL
from .coordinator import OpenAirTouchCoordinator, runtime_state


class OpenAirTouchEntity(CoordinatorEntity[OpenAirTouchCoordinator]):
    """Base entity for OpenAirTouch coordinator-backed platforms."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: OpenAirTouchCoordinator, unique_suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.instance_id}_{unique_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.instance_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name="OpenAirTouch",
        )

    @property
    def _airtouch_state(self) -> dict[str, Any]:
        return runtime_state(self.coordinator.data)
