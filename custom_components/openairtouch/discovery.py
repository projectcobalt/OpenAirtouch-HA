"""Discovery helpers for OpenAirTouch add-on instances."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, urlunparse

DEFAULT_ADDON_PORT = 8099


def url_from_hassio_discovery(discovery_info: dict[str, Any] | None) -> str | None:
    """Return an add-on API URL from Supervisor discovery data."""
    if not isinstance(discovery_info, dict):
        return None

    url = discovery_info.get("url")
    if isinstance(url, str) and url.strip():
        return _normalise_url(url)

    host = _first_string(discovery_info, ("ip_address", "host", "hostname"))
    port = _first_int(discovery_info, ("port", "api_port", "http_port")) or DEFAULT_ADDON_PORT
    if host:
        return _normalise_url(f"http://{host}:{port}")

    addon = _first_string(discovery_info, ("addon", "slug"))
    if addon:
        return _normalise_url(f"http://{_addon_hostname(addon)}:{port}")

    return None


def _normalise_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme in {"http", "https"} and parsed.hostname:
        port = parsed.port or DEFAULT_ADDON_PORT
        return urlunparse((parsed.scheme, f"{parsed.hostname}:{port}", "", "", "", ""))
    return url.strip().rstrip("/")


def _first_string(data: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_int(data: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, bool) or value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _addon_hostname(value: str) -> str:
    return value.replace("_", "-")
