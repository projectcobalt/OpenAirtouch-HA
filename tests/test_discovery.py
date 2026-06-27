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
    const.DEFAULT_URL = ""
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

    def test_hostname_is_preferred_over_ephemeral_ip_address(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({
            "ip_address": "172.30.33.4",
            "host": "d6642813-openairtouch",
        })

        self.assertEqual(url, "http://d6642813-openairtouch:8099")

    def test_ingress_port_is_used_from_installed_addon_info(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({
            "slug": "d6642813_openairtouch",
            "hostname": "d6642813-openairtouch",
            "ingress_port": 8101,
        })

        self.assertEqual(url, "http://d6642813-openairtouch:8101")

    def test_network_port_is_used_from_installed_addon_info(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({
            "slug": "d6642813_openairtouch",
            "hostname": "d6642813-openairtouch",
            "network": {"8102/tcp": None},
        })

        self.assertEqual(url, "http://d6642813-openairtouch:8102")

    def test_addon_slug_is_fallback_host(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({"addon": "openairtouch"})

        self.assertEqual(url, "http://openairtouch:8099")

    def test_installed_addon_slug_uses_container_hostname(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({"addon": "d6642813_openairtouch"})

        self.assertEqual(url, "http://d6642813-openairtouch:8099")

    def test_full_addon_slug_is_extracted_from_installed_addon_info(self) -> None:
        discovery = load_discovery_module()

        slug = discovery.addon_slug_from_hassio_info({"slug": "d6642813_openairtouch"})

        self.assertEqual(slug, "d6642813_openairtouch")

    def test_full_addon_slug_is_extracted_from_supervisor_discovery(self) -> None:
        discovery = load_discovery_module()

        slug = discovery.addon_slug_from_hassio_info({"addon": "d6642813_openairtouch"})

        self.assertEqual(slug, "d6642813_openairtouch")

    def test_hassio_service_info_uses_slug_as_container_hostname(self) -> None:
        discovery = load_discovery_module()
        discovery_info = types.SimpleNamespace(
            config={},
            name="OpenAirTouch",
            slug="d6642813_openairtouch",
            uuid="0123456789abcdef",
        )

        url = discovery.url_from_hassio_discovery(discovery_info)
        unique_id = discovery.hassio_discovery_unique_id(discovery_info, url)

        self.assertEqual(url, "http://d6642813-openairtouch:8099")
        self.assertEqual(unique_id, "0123456789abcdef")
        self.assertTrue(discovery.is_openairtouch_hassio_discovery(discovery_info))

    def test_hassio_service_info_rejects_other_addon_slugs(self) -> None:
        discovery = load_discovery_module()
        discovery_info = types.SimpleNamespace(
            config={},
            name="Matter Server",
            slug="core_matter_server",
            uuid="0123456789abcdef",
        )

        self.assertFalse(discovery.is_openairtouch_hassio_discovery(discovery_info))

    def test_supervisor_discovery_record_uses_addon_slug(self) -> None:
        discovery = load_discovery_module()
        discovery_info = types.SimpleNamespace(
            config={},
            service="openairtouch",
            addon="d6642813_openairtouch",
            uuid="fedcba9876543210",
        )

        url = discovery.url_from_hassio_discovery(discovery_info)
        unique_id = discovery.hassio_discovery_unique_id(discovery_info, url)

        self.assertEqual(url, "http://d6642813-openairtouch:8099")
        self.assertEqual(unique_id, "fedcba9876543210")
        self.assertTrue(discovery.is_openairtouch_hassio_discovery(discovery_info))

    def test_no_url_is_used_without_discovery_data(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery(None)

        self.assertIsNone(url)

    def test_service_name_alone_is_not_treated_as_hostname(self) -> None:
        discovery = load_discovery_module()

        url = discovery.url_from_hassio_discovery({"service": "openairtouch"})

        self.assertIsNone(url)


if __name__ == "__main__":
    unittest.main()
