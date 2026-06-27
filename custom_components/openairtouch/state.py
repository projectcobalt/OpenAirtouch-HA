"""Helpers for interpreting OpenAirTouch runtime state."""

from __future__ import annotations

from typing import Any


def real_ac_ids(state: dict[str, Any]) -> list[int]:
    """Return AC IDs that represent real configured AC heads."""
    system = state.get("system") or {}
    ac_count = system.get("ac_count")
    if isinstance(ac_count, bool):
        ac_count = None
    if isinstance(ac_count, int) and ac_count > 0:
        return list(range(ac_count))

    acs = state.get("acs") or {}
    if not isinstance(acs, dict):
        return []

    ids: list[int] = []
    for raw_id, record in acs.items():
        try:
            ac_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        base = (record or {}).get("base") if isinstance(record, dict) else None
        if isinstance(base, dict) and base:
            ids.append(ac_id)
    return sorted(ids)
