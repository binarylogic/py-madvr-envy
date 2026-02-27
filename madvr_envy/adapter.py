"""Home Assistant-friendly state adapter for Envy."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from madvr_envy.protocol import OptionScalar
from madvr_envy.state import EnvyState


@dataclass(frozen=True)
class EnvySnapshot:
    """Immutable, comparison-friendly view of ``EnvyState``."""

    synced: bool
    version: str | None
    is_on: bool | None
    standby: bool | None
    signal_present: bool | None
    mac_address: str | None
    active_profile_group: str | None
    active_profile_index: int | None
    current_menu: str | None
    aspect_ratio_mode: str | None
    incoming_signal: tuple[str, str, str, str, str, str, str, str, str] | None
    outgoing_signal: tuple[str, str, str, str, str, str, str, str] | None
    aspect_ratio: tuple[str, float, int, str] | None
    masking_ratio: tuple[str, float, int] | None
    tone_map_enabled: bool | None
    temperatures: tuple[int, int, int, int] | None

    settings_pages: tuple[tuple[str, str], ...]
    config_pages: tuple[tuple[str, str], ...]
    profile_groups: tuple[tuple[str, str], ...]
    profiles: tuple[tuple[str, str], ...]
    options: tuple[tuple[str, str, OptionScalar, OptionScalar], ...]

    last_system_action: str | None
    last_button_event: tuple[str, str] | None
    last_inherit_option_path: str | None
    last_inherit_option_effective: OptionScalar | None

    last_uploaded_3dlut: str | None
    last_renamed_3dlut: tuple[str, str] | None
    last_deleted_3dlut: str | None
    last_store_settings: tuple[str, str] | None
    last_restore_settings: str | None

    temporary_reset_count: int
    display_changed_count: int
    settings_upload_count: int


@dataclass(frozen=True)
class StateDelta:
    """One changed field between two snapshots."""

    field: str
    old: object
    new: object


@dataclass(frozen=True)
class AdapterEvent:
    """High-level event for integration consumers."""

    kind: str
    payload: dict[str, object]


def snapshot_from_state(state: EnvyState) -> EnvySnapshot:
    """Build an immutable snapshot from runtime state."""
    temperatures: tuple[int, int, int, int] | None = None
    if state.temperatures is not None:
        temperatures = (
            state.temperatures.gpu,
            state.temperatures.hdmi_input,
            state.temperatures.cpu,
            state.temperatures.mainboard,
        )

    options = tuple(
        (key, msg.option_type, msg.current_value, msg.effective_value)
        for key, msg in sorted(state.options.items(), key=lambda item: item[0])
    )

    inherit_path: str | None = None
    inherit_effective: OptionScalar | None = None
    if state.last_inherit_option is not None:
        inherit_path = state.last_inherit_option.option_id_path
        inherit_effective = state.last_inherit_option.effective_value

    incoming_signal: tuple[str, str, str, str, str, str, str, str, str] | None = None
    if state.incoming_signal is not None:
        incoming_signal = (
            state.incoming_signal.resolution,
            state.incoming_signal.frame_rate,
            state.incoming_signal.signal_type,
            state.incoming_signal.color_space,
            state.incoming_signal.bit_depth,
            state.incoming_signal.hdr_mode,
            state.incoming_signal.colorimetry,
            state.incoming_signal.black_levels,
            state.incoming_signal.aspect_ratio,
        )

    outgoing_signal: tuple[str, str, str, str, str, str, str, str] | None = None
    if state.outgoing_signal is not None:
        outgoing_signal = (
            state.outgoing_signal.resolution,
            state.outgoing_signal.frame_rate,
            state.outgoing_signal.signal_type,
            state.outgoing_signal.color_space,
            state.outgoing_signal.bit_depth,
            state.outgoing_signal.hdr_mode,
            state.outgoing_signal.colorimetry,
            state.outgoing_signal.black_levels,
        )

    aspect_ratio: tuple[str, float, int, str] | None = None
    if state.aspect_ratio is not None:
        aspect_ratio = (
            state.aspect_ratio.resolution,
            state.aspect_ratio.decimal_ratio,
            state.aspect_ratio.integer_ratio,
            state.aspect_ratio.name,
        )

    masking_ratio: tuple[str, float, int] | None = None
    if state.masking_ratio is not None:
        masking_ratio = (
            state.masking_ratio.resolution,
            state.masking_ratio.decimal_ratio,
            state.masking_ratio.integer_ratio,
        )

    return EnvySnapshot(
        synced=state.synced,
        version=state.version,
        is_on=state.is_on,
        standby=state.standby,
        signal_present=state.signal_present,
        mac_address=state.mac_address,
        active_profile_group=state.active_profile_group,
        active_profile_index=state.active_profile_index,
        current_menu=state.current_menu,
        aspect_ratio_mode=state.aspect_ratio_mode,
        incoming_signal=incoming_signal,
        outgoing_signal=outgoing_signal,
        aspect_ratio=aspect_ratio,
        masking_ratio=masking_ratio,
        tone_map_enabled=state.tone_map_enabled,
        temperatures=temperatures,
        settings_pages=tuple(sorted(state.settings_pages.items(), key=lambda item: item[0])),
        config_pages=tuple(sorted(state.config_pages.items(), key=lambda item: item[0])),
        profile_groups=tuple(sorted(state.profile_groups.items(), key=lambda item: item[0])),
        profiles=tuple(sorted(state.profiles.items(), key=lambda item: item[0])),
        options=options,
        last_system_action=state.last_system_action,
        last_button_event=state.last_button_event,
        last_inherit_option_path=inherit_path,
        last_inherit_option_effective=inherit_effective,
        last_uploaded_3dlut=state.last_uploaded_3dlut,
        last_renamed_3dlut=state.last_renamed_3dlut,
        last_deleted_3dlut=state.last_deleted_3dlut,
        last_store_settings=state.last_store_settings,
        last_restore_settings=state.last_restore_settings,
        temporary_reset_count=state.temporary_reset_count,
        display_changed_count=state.display_changed_count,
        settings_upload_count=state.settings_upload_count,
    )


class EnvyStateAdapter:
    """Track snapshots and expose stable deltas/events for HA coordinators."""

    def __init__(self) -> None:
        self._last_snapshot: EnvySnapshot | None = None

    @property
    def last_snapshot(self) -> EnvySnapshot | None:
        return self._last_snapshot

    def update(self, state: EnvyState) -> tuple[EnvySnapshot, list[StateDelta], list[AdapterEvent]]:
        snapshot = snapshot_from_state(state)
        previous = self._last_snapshot
        self._last_snapshot = snapshot

        if previous is None:
            return snapshot, [], []

        deltas = _build_deltas(previous, snapshot)
        events = _build_events(previous, snapshot)
        return snapshot, deltas, events


def _build_deltas(previous: EnvySnapshot, current: EnvySnapshot) -> list[StateDelta]:
    deltas: list[StateDelta] = []
    for field_def in fields(EnvySnapshot):
        name = field_def.name
        old_value = getattr(previous, name)
        new_value = getattr(current, name)
        if old_value != new_value:
            deltas.append(StateDelta(field=name, old=old_value, new=new_value))
    return deltas


def _counter_event(
    kind: str,
    previous: EnvySnapshot,
    current: EnvySnapshot,
    field_name: str,
) -> AdapterEvent | None:
    old_value = getattr(previous, field_name)
    new_value = getattr(current, field_name)
    if not isinstance(old_value, int) or not isinstance(new_value, int) or new_value <= old_value:
        return None
    return AdapterEvent(
        kind=kind,
        payload={
            "count": new_value,
            "increment": new_value - old_value,
        },
    )


def _change_event(kind: str, old_value: Any, new_value: Any, payload_key: str = "value") -> AdapterEvent | None:
    if new_value is None or new_value == old_value:
        return None
    return AdapterEvent(kind=kind, payload={payload_key: new_value})


def _build_events(previous: EnvySnapshot, current: EnvySnapshot) -> list[AdapterEvent]:
    events: list[AdapterEvent] = []

    for event in (
        _counter_event("temporary_reset", previous, current, "temporary_reset_count"),
        _counter_event("display_changed", previous, current, "display_changed_count"),
        _counter_event("settings_uploaded", previous, current, "settings_upload_count"),
        _change_event("system_action", previous.last_system_action, current.last_system_action, "action"),
        _change_event("button", previous.last_button_event, current.last_button_event, "button"),
        _change_event("option_inherited", previous.last_inherit_option_path, current.last_inherit_option_path, "path"),
        _change_event("lut_uploaded", previous.last_uploaded_3dlut, current.last_uploaded_3dlut, "filename"),
        _change_event("lut_renamed", previous.last_renamed_3dlut, current.last_renamed_3dlut, "rename"),
        _change_event("lut_deleted", previous.last_deleted_3dlut, current.last_deleted_3dlut, "filename"),
        _change_event("settings_stored", previous.last_store_settings, current.last_store_settings, "store"),
        _change_event("settings_restored", previous.last_restore_settings, current.last_restore_settings, "target"),
    ):
        if event is not None:
            events.append(event)

    return events
