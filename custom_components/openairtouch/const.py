"""Constants for the OpenAirTouch integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "openairtouch"
DEFAULT_URL: Final = "http://a0d7b954-openairtouch:8099"
CONF_URL: Final = "url"

ATTRIBUTION: Final = "Data provided by the OpenAirTouch add-on"
MANUFACTURER: Final = "Polyaire"
MODEL: Final = "OpenAirTouch"

PLATFORMS: Final = [
    Platform.CLIMATE,
    Platform.COVER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]
