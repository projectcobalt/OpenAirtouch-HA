"""Discovery helpers for OpenAirTouch add-on instances."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, urlunparse

DEFAULT_ADDON_PORT = 8099
ADDON_SLUG = "openairtouch"


def url_from_hassio_discovery(discovery_info: Any) -> str | None:
    """Return an add-on API URL from Supervisor discovery data."""
    discovery_data = hassio_discovery_data(discovery_info)
    if discovery_data is None:
        return None

    url = discovery_data.get("url")
    if isinstance(url, str) and url.strip():
        return normalise_url(url)

    host = _first_string(discovery_data, ("ip_address", "host", "hostname"))
    port = _first_int(discovery_data, ("port", "api_port", "http_port")) or DEFAULT_ADDON_PORT
    if host:
        return normalise_url(f"http://{host}:{port}")

    addon = _first_string(discovery_data, ("slug", "addon"))
    if addon:
        return normalise_url(f"http://{_addon_hostname(addon)}:{port}")

    return None


def hassio_discovery_data(discovery_info: Any) -> dict[str, Any] | None:
    """Return normalized discovery data from HA's HassioServiceInfo or a dict."""
    if isinstance(discovery_info, dict):
        return discovery_info

    config = getattr(discovery_info, "config", None)
    data = dict(config) if isinstance(config, dict) else {}
    for attr in ("addon", "service", "slug", "name", "uuid"):
        value = getattr(discovery_info, attr, None)
        if value is not None:
            data[attr] = value
    return data or None


def hassio_discovery_unique_id(discovery_info: Any, fallback_url: str) -> str:
    """Return the config-entry unique ID for a hassio discovery payload."""
    uuid = getattr(discovery_info, "uuid", None)
    if isinstance(uuid, str) and uuid:
        return uuid
    if isinstance(discovery_info, dict):
        uuid = discovery_info.get("uuid")
        if isinstance(uuid, str) and uuid:
            return uuid
    return fallback_url


def is_openairtouch_hassio_discovery(discovery_info: Any) -> bool:
    """Return whether a hassio discovery payload belongs to OpenAirTouch."""
    data = hassio_discovery_data(discovery_info)
    if data is None:
        return False
    slug = data.get("slug")
    if isinstance(slug, str) and (slug == ADDON_SLUG or slug.endswith(f"_{ADDON_SLUG}")):
        return True
    service = data.get("service")
    return service == ADDON_SLUG


def normalise_url(url: str) -> str:
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
