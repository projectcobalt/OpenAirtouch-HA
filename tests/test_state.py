"""Tests for OpenAirTouch runtime state helpers."""

from __future__ import annotations

import importlib.util
import types
import unittest
from pathlib import Path


def load_state_module() -> types.ModuleType:
    path = Path(__file__).parents[1] / "custom_components" / "openairtouch" / "state.py"
    spec = importlib.util.spec_from_file_location("openairtouch_state_under_test", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class OpenAirTouchStateTests(unittest.TestCase):
    def test_real_ac_ids_use_system_ac_count(self) -> None:
        state = load_state_module()

        ac_ids = state.real_ac_ids({
            "system": {"ac_count": 1},
            "acs": {
                "0": {"base": {"name": "Home"}},
                "1": None,
                "2": None,
                "3": None,
            },
        })

        self.assertEqual(ac_ids, [0])

    def test_real_ac_ids_fall_back_to_populated_base_records(self) -> None:
        state = load_state_module()

        ac_ids = state.real_ac_ids({
            "acs": {
                "0": {"base": {"name": "Downstairs"}},
                "1": None,
                "2": {"base": {"name": "Upstairs"}},
                "3": {},
            },
        })

        self.assertEqual(ac_ids, [0, 2])

    def test_real_ac_ids_ignore_invalid_count_and_placeholder_records(self) -> None:
        state = load_state_module()

        ac_ids = state.real_ac_ids({
            "system": {"ac_count": 0},
            "acs": {
                "0": None,
                "1": {"base": {}},
                "not-an-int": {"base": {"name": "Invalid"}},
            },
        })

        self.assertEqual(ac_ids, [])


if __name__ == "__main__":
    unittest.main()
