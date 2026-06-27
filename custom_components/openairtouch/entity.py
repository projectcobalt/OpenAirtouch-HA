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


def ac_device_info(coordinator: OpenAirTouchCoordinator, ac_id: int, name: str | None = None) -> DeviceInfo:
    """Return device info for an AC head."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{coordinator.instance_id}_ac_{ac_id}")},
        manufacturer=MANUFACTURER,
        model=MODEL,
        name=name or f"AC {ac_id + 1}",
    )


def zone_device_info(
    coordinator: OpenAirTouchCoordinator,
    group_id: int,
    *,
    ac_id: int | None = None,
    name: str | None = None,
) -> DeviceInfo:
    """Return device info for a zone."""
    info = DeviceInfo(
        identifiers={(DOMAIN, f"{coordinator.instance_id}_zone_{group_id}")},
        manufacturer=MANUFACTURER,
        model="OpenAirTouch Zone",
        name=name or f"Zone {group_id + 1}",
    )
    if ac_id is not None:
        info["via_device"] = (DOMAIN, f"{coordinator.instance_id}_ac_{ac_id}")
    return info


def sensor_device_info(
    coordinator: OpenAirTouchCoordinator,
    sensor_id: str,
    *,
    kind: str | None = None,
    name: str | None = None,
) -> DeviceInfo:
    """Return device info for an AirTouch RF sensor or touchpad."""
    sensor_kind = kind or "sensor"
    label = name or f"{sensor_kind.replace('_', ' ').title()} {sensor_id}"
    return DeviceInfo(
        identifiers={(DOMAIN, f"{coordinator.instance_id}_{sensor_kind}_{sensor_id}")},
        manufacturer=MANUFACTURER,
        model=f"OpenAirTouch {sensor_kind.replace('_', ' ').title()}",
        name=label,
    )
