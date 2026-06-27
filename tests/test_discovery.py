"""Tests for OpenAirTouch add-on discovery helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


def load_discovery_module() -> types.ModuleType:
    """Load discovery.py with a stub package so Home Assistant is not required."""
    package = types.ModuleType("custom_components.openairtouch")
    package.__path__ = []
    sys.modules["custom_components"] = types.ModuleType("custom_components")
    sys.modules["custom_components.openairtouch"] = package

    const = types.ModuleType("custom_components.openairtouch.const")
    const.DEFAULT_URL = "http://a0d7b954-openairtouch:8099"
    sys.modules["custom_components.openairtouch.const"] = const

    path = Path(__file__).parents[1] / "custom_components" / "openairtouch" / "discovery.py"
    spec = importlib.util.spec_from_file_location("custom_components.openairtouch.discovery", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class OpenAirTouchDiscoveryTests(unittest.TestCase):
    def test_explicit_url_is_used_first(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({"url": "http://openairtouch.local:8099/"})

        self.assertEqual(url, "http://openairtouch.local:8099")

    def test_explicit_url_path_is_normalized_to_base_url(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({"url": "http://openairtouch:8099/api/state"})

        self.assertEqual(url, "http://openairtouch:8099")

    def test_host_and_port_build_addon_url(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({"host": "abc-openairtouch", "port": "8099"})

        self.assertEqual(url, "http://abc-openairtouch:8099")

    def test_addon_slug_is_fallback_host(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({"addon": "openairtouch"})

        self.assertEqual(url, "http://openairtouch:8099")

    def test_installed_addon_slug_uses_container_hostname(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({"addon": "d6642813_openairtouch"})

        self.assertEqual(url, "http://d6642813-openairtouch:8099")

    def test_service_name_is_fallback_host(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({"service": "openairtouch"})

        self.assertEqual(url, "http://openairtouch:8099")

    def test_default_url_is_used_without_discovery_data(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery(None)

        self.assertEqual(url, "http://a0d7b954-openairtouch:8099")


if __name__ == "__main__":
    unittest.main()
