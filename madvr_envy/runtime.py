"""Semantic runtime models for Envy integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from madvr_envy.adapter import EnvySnapshot, snapshot_from_state
from madvr_envy.state import EnvyState


class PowerState(StrEnum):
    """Normalized device lifecycle state."""

    ON = "on"
    STANDBY = "standby"
    OFF = "off"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class EnvyRuntimeSnapshot:
    """Stable semantic view of the current Envy runtime state."""

    power_state: PowerState
    connected: bool
    synced: bool
    version: str | None
    mac_address: str | None
    signal_present: bool | None
    current_menu: str | None
    aspect_ratio_mode: str | None
    active_profile_group: str | None
    active_profile_index: int | None
    tone_map_enabled: bool | None
    temperatures: tuple[int, int, int, int] | None
    incoming_signal: dict[str, str] | None
    outgoing_signal: dict[str, str] | None
    aspect_ratio: dict[str, str | float] | None
    masking_ratio: dict[str, float] | None
    profile_groups: dict[str, str] = field(default_factory=dict)
    profiles: dict[str, str] = field(default_factory=dict)


def power_state_from_snapshot(snapshot: EnvySnapshot) -> PowerState:
    """Normalize raw snapshot flags to a single power-state enum."""
    if snapshot.is_on is True:
        return PowerState.ON
    if snapshot.standby is True:
        return PowerState.STANDBY
    if snapshot.is_on is False:
        return PowerState.OFF
    return PowerState.UNKNOWN


def runtime_snapshot_from_snapshot(
    snapshot: EnvySnapshot,
    *,
    connected: bool,
) -> EnvyRuntimeSnapshot:
    """Build a semantic runtime snapshot from an adapter snapshot."""
    return EnvyRuntimeSnapshot(
        power_state=power_state_from_snapshot(snapshot),
        connected=connected,
        synced=snapshot.synced,
        version=snapshot.version,
        mac_address=snapshot.mac_address,
        signal_present=snapshot.signal_present,
        current_menu=snapshot.current_menu,
        aspect_ratio_mode=snapshot.aspect_ratio_mode,
        active_profile_group=snapshot.active_profile_group,
        active_profile_index=snapshot.active_profile_index,
        tone_map_enabled=snapshot.tone_map_enabled,
        temperatures=snapshot.temperatures,
        incoming_signal=_signal_map(snapshot.incoming_signal),
        outgoing_signal=_output_signal_map(snapshot.outgoing_signal),
        aspect_ratio=_aspect_ratio_map(snapshot.aspect_ratio),
        masking_ratio=_masking_ratio_map(snapshot.masking_ratio),
        profile_groups=dict(snapshot.profile_groups),
        profiles=dict(snapshot.profiles),
    )


def runtime_snapshot_from_state(state: EnvyState, *, connected: bool) -> EnvyRuntimeSnapshot:
    """Build a semantic runtime snapshot directly from runtime state."""
    return runtime_snapshot_from_snapshot(snapshot_from_state(state), connected=connected)


def _signal_map(value: tuple[str, str, str, str, str, str, str, str, str] | None) -> dict[str, str] | None:
    if value is None:
        return None
    return {
        "resolution": value[0],
        "frame_rate": value[1],
        "signal_type": value[2],
        "color_space": value[3],
        "bit_depth": value[4],
        "hdr_mode": value[5],
        "colorimetry": value[6],
        "black_levels": value[7],
        "aspect_ratio": value[8],
    }


def _output_signal_map(value: tuple[str, str, str, str, str, str, str, str] | None) -> dict[str, str] | None:
    if value is None:
        return None
    return {
        "resolution": value[0],
        "frame_rate": value[1],
        "signal_type": value[2],
        "color_space": value[3],
        "bit_depth": value[4],
        "hdr_mode": value[5],
        "colorimetry": value[6],
        "black_levels": value[7],
    }


def _aspect_ratio_map(value: tuple[str, float, int, str] | None) -> dict[str, str | float] | None:
    if value is None:
        return None
    return {
        "resolution": value[0],
        "decimal_ratio": value[1],
        "name": value[3],
    }


def _masking_ratio_map(value: tuple[str, float, int] | None) -> dict[str, float] | None:
    if value is None:
        return None
    return {
        "decimal_ratio": value[1],
    }
