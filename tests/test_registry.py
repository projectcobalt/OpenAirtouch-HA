"""Tests for OpenAirTouch registry migration helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


def load_registry_module() -> types.ModuleType:
    """Load registry.py with Home Assistant stubs so HA is not required."""
    package = types.ModuleType("custom_components.openairtouch")
    package.__path__ = []
    sys.modules["custom_components"] = types.ModuleType("custom_components")
    sys.modules["custom_components.openairtouch"] = package

    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    entity_registry.EntityRegistry = object
    helpers = types.ModuleType("homeassistant.helpers")
    helpers.entity_registry = entity_registry
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.helpers = helpers
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.entity_registry"] = entity_registry

    const = types.ModuleType("custom_components.openairtouch.const")
    const.CONF_INSTANCE_ID = "instance_id"
    const.CONF_URL = "url"
    const.DOMAIN = "openairtouch"
    sys.modules["custom_components.openairtouch.const"] = const

    state_path = Path(__file__).parents[1] / "custom_components" / "openairtouch" / "state.py"
    state_spec = importlib.util.spec_from_file_location("custom_components.openairtouch.state", state_path)
    assert state_spec is not None
    state = importlib.util.module_from_spec(state_spec)
    assert state_spec.loader is not None
    state_spec.loader.exec_module(state)
    sys.modules["custom_components.openairtouch.state"] = state

    path = Path(__file__).parents[1] / "custom_components" / "openairtouch" / "registry.py"
    spec = importlib.util.spec_from_file_location("custom_components.openairtouch.registry", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeEntry:
    entry_id = "abc123"
    unique_id = "http://172.30.33.4:8099"

    def __init__(self, data: dict[str, str]) -> None:
        self.data = data


class OpenAirTouchRegistryTests(unittest.TestCase):
    def test_instance_id_for_entry_uses_stored_value_or_entry_id(self) -> None:
        registry = load_registry_module()

        self.assertEqual(registry.instance_id_for_entry(FakeEntry({"instance_id": "stored"})), "stored")
        self.assertEqual(registry.instance_id_for_entry(FakeEntry({"url": "http://addon:8099"})), "entry_abc123")

    def test_migrate_unique_id_replaces_legacy_instance_prefix(self) -> None:
        registry = load_registry_module()

        migrated = registry.migrate_unique_id(
            "openairtouch_http://172.30.33.4:8099_zone_1_climate",
            "entry_abc123",
            ["http://172.30.33.4:8099"],
        )

        self.assertEqual(migrated, "openairtouch_entry_abc123_zone_1_climate")

    def test_stale_unique_ids_include_removed_zone_temps_and_touchpad_battery(self) -> None:
        registry = load_registry_module()

        stale = registry.stale_unique_ids(
            "entry_abc123",
            {
                "system": {"ac_count": 1},
                "active_groups": {
                    "0": {"status": {"has_sensor": True}},
                    "1": {"status": {"has_sensor": True}},
                },
                "sensor_view": [
                    {"id": 144, "kind": "touchpad"},
                    {"id": 1, "kind": "supply_air", "ac": 0},
                    {"id": 2, "kind": "supply_air", "ac": 1},
                ],
            },
        )

        self.assertIn("openairtouch_entry_abc123_zone_1_temperature", stale)
        self.assertIn("openairtouch_entry_abc123_sensor_144_low_battery", stale)
        self.assertIn("openairtouch_entry_abc123_sensor_2_temperature", stale)
        self.assertNotIn("openairtouch_entry_abc123_sensor_1_temperature", stale)


if __name__ == "__main__":
    unittest.main()
