"""Helpers for adapting adapter output to Home Assistant-friendly payloads."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from madvr_envy.adapter import AdapterEvent, EnvySnapshot, StateDelta


@dataclass(frozen=True)
class HABusEvent:
    """Home Assistant event bus payload."""

    event_type: str
    event_data: dict[str, object]


@dataclass(frozen=True)
class HABridgeUpdate:
    """Coordinator update package derived from adapter output."""

    coordinator_data: dict[str, Any]
    changed_fields: tuple[str, ...]
    bus_events: tuple[HABusEvent, ...]


EventEmitter = Callable[[str, dict[str, object]], None]


def _power_state(snapshot: EnvySnapshot) -> str:
    if snapshot.is_on is True:
        return "on"
    if snapshot.standby is True:
        return "standby"
    if snapshot.is_on is False:
        return "off"
    return "unknown"


def coordinator_payload(snapshot: EnvySnapshot) -> dict[str, Any]:
    """Build one coordinator payload dictionary from a snapshot."""
    return {
        "available": snapshot.synced,
        "power_state": _power_state(snapshot),
        "version": snapshot.version,
        "signal_present": snapshot.signal_present,
        "mac_address": snapshot.mac_address,
        "active_profile_group": snapshot.active_profile_group,
        "active_profile_index": snapshot.active_profile_index,
        "current_menu": snapshot.current_menu,
        "aspect_ratio_mode": snapshot.aspect_ratio_mode,
        "tone_map_enabled": snapshot.tone_map_enabled,
        "temperatures": snapshot.temperatures,
        "settings_pages": dict(snapshot.settings_pages),
        "config_pages": dict(snapshot.config_pages),
        "profile_groups": dict(snapshot.profile_groups),
        "profiles": dict(snapshot.profiles),
        "options": {
            key: {
                "type": option_type,
                "current": current_value,
                "effective": effective_value,
            }
            for key, option_type, current_value, effective_value in snapshot.options
        },
        "last_system_action": snapshot.last_system_action,
        "last_button_event": snapshot.last_button_event,
        "last_inherit_option_path": snapshot.last_inherit_option_path,
        "last_inherit_option_effective": snapshot.last_inherit_option_effective,
        "last_uploaded_3dlut": snapshot.last_uploaded_3dlut,
        "last_renamed_3dlut": snapshot.last_renamed_3dlut,
        "last_deleted_3dlut": snapshot.last_deleted_3dlut,
        "last_store_settings": snapshot.last_store_settings,
        "last_restore_settings": snapshot.last_restore_settings,
        "temporary_reset_count": snapshot.temporary_reset_count,
        "display_changed_count": snapshot.display_changed_count,
        "settings_upload_count": snapshot.settings_upload_count,
    }


def to_ha_events(events: list[AdapterEvent]) -> tuple[HABusEvent, ...]:
    """Map adapter events to HA event bus objects."""
    mapped: list[HABusEvent] = []
    for event in events:
        mapped.append(
            HABusEvent(
                event_type=f"madvr_envy.{event.kind}",
                event_data=dict(event.payload),
            )
        )
    return tuple(mapped)


def build_bridge_update(
    snapshot: EnvySnapshot,
    deltas: list[StateDelta],
    events: list[AdapterEvent],
) -> HABridgeUpdate:
    """Build one Home Assistant bridge update from adapter output."""
    return HABridgeUpdate(
        coordinator_data=coordinator_payload(snapshot),
        changed_fields=tuple(delta.field for delta in deltas),
        bus_events=to_ha_events(events),
    )


class HABridgeDispatcher:
    """Runtime helper that converts adapter updates and dispatches bus events."""

    def __init__(self, event_emitter: EventEmitter | None = None) -> None:
        self._event_emitter = event_emitter
        self.last_update: HABridgeUpdate | None = None

    def handle_adapter_update(
        self,
        snapshot: EnvySnapshot,
        deltas: list[StateDelta],
        events: list[AdapterEvent],
    ) -> HABridgeUpdate:
        update = build_bridge_update(snapshot, deltas, events)
        self.last_update = update

        if self._event_emitter is not None:
            for event in update.bus_events:
                self._event_emitter(event.event_type, event.event_data)

        return update
