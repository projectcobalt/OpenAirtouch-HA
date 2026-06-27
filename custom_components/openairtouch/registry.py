"""Entity registry migration helpers for OpenAirTouch."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_INSTANCE_ID, CONF_URL, DOMAIN
from .state import group_records, real_ac_ids


def instance_id_for_entry(entry: ConfigEntry) -> str:
    """Return a stable integration instance ID for entity/device identifiers."""
    stored = entry.data.get(CONF_INSTANCE_ID)
    return str(stored) if stored else f"entry_{entry.entry_id}"


def legacy_instance_ids(entry: ConfigEntry, instance_id: str) -> list[str]:
    """Return older instance identifiers that may exist in the entity registry."""
    values = [entry.unique_id, entry.data.get(CONF_URL)]
    seen: set[str] = {instance_id}
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


async def async_migrate_registry_entries(
    hass: HomeAssistant,
    entry: ConfigEntry,
    instance_id: str,
    state: dict[str, Any],
) -> None:
    """Migrate legacy entity unique IDs and remove known stale entries."""
    registry = er.async_get(hass)
    legacy_ids = legacy_instance_ids(entry, instance_id)
    stale_ids = stale_unique_ids(instance_id, state)
    for legacy_id in legacy_ids:
        stale_ids.update(stale_unique_ids(legacy_id, state))

    for entity_entry in list(er.async_entries_for_config_entry(registry, entry.entry_id)):
        unique_id = entity_entry.unique_id
        migrated_unique_id = migrate_unique_id(unique_id, instance_id, legacy_ids)
        if migrated_unique_id != unique_id:
            if _entity_id_for_unique_id(registry, entity_entry.domain, migrated_unique_id) is None:
                registry.async_update_entity(entity_entry.entity_id, new_unique_id=migrated_unique_id)
                unique_id = migrated_unique_id

        if unique_id in stale_ids:
            registry.async_remove(entity_entry.entity_id)


def migrate_unique_id(unique_id: str | None, instance_id: str, legacy_ids: list[str]) -> str | None:
    """Return a stable unique ID when an older instance prefix is present."""
    if not unique_id:
        return unique_id
    for legacy_id in legacy_ids:
        legacy_prefix = f"{DOMAIN}_{legacy_id}_"
        if unique_id.startswith(legacy_prefix):
            return f"{DOMAIN}_{instance_id}_{unique_id[len(legacy_prefix):]}"
    return unique_id


def stale_unique_ids(instance_id: str, state: dict[str, Any]) -> set[str]:
    """Return stale entity unique IDs removed by recent entity-model cleanup."""
    stale: set[str] = set()

    for group_id in group_records(state):
        stale.add(_unique_id(instance_id, f"zone_{group_id + 1}_temperature"))

    for row in state.get("sensor_view") or []:
        if not isinstance(row, dict) or "id" not in row:
            continue
        sensor_suffix = _safe_id(str(row["id"]))
        if row.get("kind") == "touchpad":
            stale.add(_unique_id(instance_id, f"sensor_{sensor_suffix}_low_battery"))
        if row.get("kind") == "supply_air" and row.get("ac") not in real_ac_ids(state):
            stale.add(_unique_id(instance_id, f"sensor_{sensor_suffix}_temperature"))

    return stale


def _entity_id_for_unique_id(
    registry: er.EntityRegistry,
    domain: str,
    unique_id: str,
) -> str | None:
    return registry.async_get_entity_id(domain, DOMAIN, unique_id)


def _unique_id(instance_id: str, suffix: str) -> str:
    return f"{DOMAIN}_{instance_id}_{suffix}"


def _safe_id(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_") or "unknown"
