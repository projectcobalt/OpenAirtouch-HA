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


def group_records(state: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Return integer-keyed group records from the active group set."""
    groups = state.get("active_groups") or state.get("groups") or {}
    if not isinstance(groups, dict):
        return {}

    records: dict[int, dict[str, Any]] = {}
    for raw_id, record in groups.items():
        try:
            group_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if isinstance(record, dict):
            records[group_id] = record
    return records


def spill_group_ids(state: dict[str, Any]) -> set[int]:
    """Return zero-based group IDs configured as spill zones."""
    spill = (state.get("system") or {}).get("spill") or {}
    ids = spill.get("spill_groups_zero_based")
    if not isinstance(ids, list):
        ids = spill.get("groups_zero_based")
    if not isinstance(ids, list):
        return set()
    result: set[int] = set()
    for value in ids:
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            continue
    return result


def real_zone_ids(state: dict[str, Any]) -> list[int]:
    """Return group IDs that should be exposed as real zone devices."""
    spill_ids = spill_group_ids(state)
    return [group_id for group_id in sorted(group_records(state)) if group_id not in spill_ids]


def ac_id_for_group(state: dict[str, Any], group_id: int) -> int | None:
    """Return the AC ID that owns a group, based on AC group ranges."""
    for ac_id in real_ac_ids(state):
        record = (state.get("acs") or {}).get(ac_id) or (state.get("acs") or {}).get(str(ac_id)) or {}
        base = record.get("base") if isinstance(record, dict) else None
        if not isinstance(base, dict):
            continue
        start = base.get("group_start")
        count = base.get("group_count")
        if isinstance(start, int) and isinstance(count, int) and start <= group_id < start + count:
            return ac_id
    ids = real_ac_ids(state)
    return ids[0] if len(ids) == 1 else None


def zone_id_for_sensor_row(state: dict[str, Any], row: dict[str, Any]) -> int | None:
    """Return the owning zone ID for an RF sensor row when it maps cleanly."""
    if row.get("kind") != "rf":
        return None
    try:
        sensor_id = int(row.get("id"))
    except (TypeError, ValueError):
        return None
    if sensor_id % 2:
        return None

    group_id = sensor_id // 2
    if group_id not in real_zone_ids(state):
        return None
    status = (group_records(state).get(group_id) or {}).get("status") or {}
    return group_id if status.get("has_sensor") is True else None
