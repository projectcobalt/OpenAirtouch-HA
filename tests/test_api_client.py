"""Tests for the OpenAirTouch HTTP client without Home Assistant installed."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any


class FakeClientError(Exception):
    """Stand-in for aiohttp.ClientError."""


def load_api_module() -> types.ModuleType:
    """Load api.py directly so package imports do not require Home Assistant."""
    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientError = FakeClientError
    aiohttp.ClientSession = object
    sys.modules["aiohttp"] = aiohttp

    path = Path(__file__).parents[1] / "custom_components" / "openairtouch" / "api.py"
    spec = importlib.util.spec_from_file_location("openairtouch_api_under_test", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.closed = False

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        self.closed = True

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self, payloads: dict[tuple[str, str], Any]) -> None:
        self.payloads = payloads
        self.calls: list[tuple[str, str, Any]] = []

    def get(self, url: str) -> FakeResponse:
        self.calls.append(("GET", url, None))
        return FakeResponse(self.payloads[("GET", url)])

    def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
        self.calls.append(("POST", url, json))
        return FakeResponse(self.payloads[("POST", url)])


class OpenAirTouchClientTests(unittest.TestCase):
    def test_health_state_and_command_use_addon_api_contract(self) -> None:
        api = load_api_module()
        session = FakeSession(
            {
                ("GET", "http://addon:8099/api/health"): {"status": "running"},
                ("GET", "http://addon:8099/api/state"): {"runtime": {"state": {}}},
                ("GET", "http://addon:8099/api/events"): {"events": []},
                ("POST", "http://addon:8099/api/command"): {"queued": True},
            }
        )
        client = api.OpenAirTouchClient(session, "http://addon:8099/")

        health = asyncio.run(client.health())
        state = asyncio.run(client.state())
        events = asyncio.run(client.events())
        result = asyncio.run(client.command("group_percentage", {"group": 1, "percentage": 50}))

        self.assertEqual(health, {"status": "running"})
        self.assertEqual(state, {"runtime": {"state": {}}})
        self.assertEqual(events, {"events": []})
        self.assertEqual(result, {"queued": True})
        self.assertEqual(
            session.calls,
            [
                ("GET", "http://addon:8099/api/health", None),
                ("GET", "http://addon:8099/api/state", None),
                ("GET", "http://addon:8099/api/events", None),
                (
                    "POST",
                    "http://addon:8099/api/command",
                    {"action": "group_percentage", "data": {"group": 1, "percentage": 50}},
                ),
            ],
        )

    def test_non_object_response_raises_api_error(self) -> None:
        api = load_api_module()
        session = FakeSession({("GET", "http://addon:8099/api/state"): []})
        client = api.OpenAirTouchClient(session, "http://addon:8099")

        with self.assertRaises(api.OpenAirTouchApiError):
            asyncio.run(client.state())


if __name__ == "__main__":
    unittest.main()
