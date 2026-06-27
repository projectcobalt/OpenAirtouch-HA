"""Constants for the OpenAirTouch integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "openairtouch"
DEFAULT_URL: Final = ""
CONF_URL: Final = "url"
CONF_INSTANCE_ID: Final = "instance_id"

ATTRIBUTION: Final = "Data provided by the OpenAirTouch add-on"
MANUFACTURER: Final = "Polyaire"
MODEL: Final = "OpenAirTouch"

PLATFORMS: Final = [
    Platform.CLIMATE,
    Platform.COVER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]
