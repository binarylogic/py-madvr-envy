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
class SignalInfo:
    """One HDMI signal description."""

    resolution: str
    frame_rate: str
    signal_type: str
    color_space: str
    bit_depth: str
    hdr_mode: str
    colorimetry: str
    black_levels: str
    aspect_ratio: str | None = None


@dataclass(frozen=True, slots=True)
class AspectRatio:
    """Current content aspect ratio."""

    resolution: str
    decimal_ratio: float
    integer_ratio: int
    name: str


@dataclass(frozen=True, slots=True)
class MaskingRatio:
    """Current masking ratio."""

    resolution: str
    decimal_ratio: float
    integer_ratio: int


@dataclass(frozen=True, slots=True)
class Temperatures:
    """Device temperature readings."""

    gpu: int
    hdmi_input: int
    cpu: int
    mainboard: int

    @property
    def values(self) -> tuple[int, int, int, int]:
        """Return readings in stable GPU, HDMI input, CPU, mainboard order."""
        return (self.gpu, self.hdmi_input, self.cpu, self.mainboard)


@dataclass(frozen=True, slots=True)
class Profile:
    """One selectable madVR profile."""

    profile_id: str
    group_id: str
    index: str
    name: str


@dataclass(frozen=True, slots=True)
class ProfileGroup:
    """One madVR profile group."""

    group_id: str
    name: str


@dataclass(frozen=True, slots=True)
class ActiveProfile:
    """Current active profile pointer."""

    group_id: str
    index: str


@dataclass(frozen=True, slots=True)
class ProfileCatalog:
    """Typed profile catalog and active selection."""

    groups: tuple[ProfileGroup, ...] = ()
    profiles: tuple[Profile, ...] = ()
    active_profiles: tuple[ActiveProfile, ...] = ()

    @property
    def available(self) -> bool:
        """Return whether the catalog has selectable profiles."""
        return bool(self.groups and self.profiles)

    def group_name(self, group_id: str) -> str:
        """Return the display name for a group id."""
        for group in self.groups:
            if group.group_id == group_id:
                return group.name
        return group_id

    def active_for_group(self, group_id: str) -> ActiveProfile | None:
        """Return the reported active profile for a group."""
        for active in self.active_profiles:
            if active.group_id == group_id:
                return active
        return None

    def active_profile_name(self, group_id: str) -> str | None:
        """Return a stable label for one group's active profile."""
        active = self.active_for_group(group_id)
        if active is None:
            return None
        group_name = self.group_name(active.group_id)
        for profile in self.profiles:
            if profile.group_id == active.group_id and profile.index == active.index:
                return f"{group_name}: {profile.name}"
        return f"{group_name}: {active.index}"


@dataclass(frozen=True, slots=True)
class EnvyDeviceSnapshot:
    """Stable semantic view of the current Envy device state."""

    power_state: PowerState = PowerState.UNKNOWN
    connected: bool = False
    synced: bool = False
    version: str | None = None
    mac_address: str | None = None
    signal_present: bool | None = None
    current_menu: str | None = None
    aspect_ratio_mode: str | None = None
    tone_map_enabled: bool | None = None
    temperatures: Temperatures | None = None
    incoming_signal: SignalInfo | None = None
    outgoing_signal: SignalInfo | None = None
    aspect_ratio: AspectRatio | None = None
    masking_ratio: MaskingRatio | None = None
    profiles: ProfileCatalog = field(default_factory=ProfileCatalog)

    @property
    def is_awake(self) -> bool:
        """Return whether live telemetry/control state is meaningful."""
        return self.power_state is PowerState.ON and self.connected and self.synced

    @property
    def can_send_live_commands(self) -> bool:
        """Return whether commands can be sent over the active transport."""
        return self.connected and self.synced


def power_state_from_snapshot(snapshot: EnvySnapshot) -> PowerState:
    """Normalize raw snapshot flags to a single power-state enum."""
    if snapshot.is_on is True:
        return PowerState.ON
    if snapshot.standby is True:
        return PowerState.STANDBY
    if snapshot.is_on is False:
        return PowerState.OFF
    return PowerState.UNKNOWN


def device_snapshot_from_snapshot(
    snapshot: EnvySnapshot,
    *,
    connected: bool,
) -> EnvyDeviceSnapshot:
    """Build a semantic device snapshot from an adapter snapshot."""
    return EnvyDeviceSnapshot(
        power_state=power_state_from_snapshot(snapshot),
        connected=connected,
        synced=snapshot.synced,
        version=snapshot.version,
        mac_address=snapshot.mac_address,
        signal_present=snapshot.signal_present,
        current_menu=snapshot.current_menu,
        aspect_ratio_mode=snapshot.aspect_ratio_mode,
        tone_map_enabled=snapshot.tone_map_enabled,
        temperatures=_temperatures(snapshot.temperatures),
        incoming_signal=_incoming_signal(snapshot.incoming_signal),
        outgoing_signal=_outgoing_signal(snapshot.outgoing_signal),
        aspect_ratio=_aspect_ratio(snapshot.aspect_ratio),
        masking_ratio=_masking_ratio(snapshot.masking_ratio),
        profiles=_profile_catalog(snapshot),
    )


def device_snapshot_from_state(state: EnvyState, *, connected: bool) -> EnvyDeviceSnapshot:
    """Build a semantic device snapshot directly from runtime state."""
    return device_snapshot_from_snapshot(snapshot_from_state(state), connected=connected)


def _incoming_signal(value: tuple[str, str, str, str, str, str, str, str, str] | None) -> SignalInfo | None:
    if value is None:
        return None
    return SignalInfo(
        resolution=value[0],
        frame_rate=value[1],
        signal_type=value[2],
        color_space=value[3],
        bit_depth=value[4],
        hdr_mode=value[5],
        colorimetry=value[6],
        black_levels=value[7],
        aspect_ratio=value[8],
    )


def _outgoing_signal(value: tuple[str, str, str, str, str, str, str, str] | None) -> SignalInfo | None:
    if value is None:
        return None
    return SignalInfo(
        resolution=value[0],
        frame_rate=value[1],
        signal_type=value[2],
        color_space=value[3],
        bit_depth=value[4],
        hdr_mode=value[5],
        colorimetry=value[6],
        black_levels=value[7],
    )


def _aspect_ratio(value: tuple[str, float, int, str] | None) -> AspectRatio | None:
    if value is None:
        return None
    return AspectRatio(
        resolution=value[0],
        decimal_ratio=value[1],
        integer_ratio=value[2],
        name=value[3],
    )


def _masking_ratio(value: tuple[str, float, int] | None) -> MaskingRatio | None:
    if value is None:
        return None
    return MaskingRatio(
        resolution=value[0],
        decimal_ratio=value[1],
        integer_ratio=value[2],
    )


def _temperatures(value: tuple[int, int, int, int] | None) -> Temperatures | None:
    if value is None:
        return None
    return Temperatures(
        gpu=value[0],
        hdmi_input=value[1],
        cpu=value[2],
        mainboard=value[3],
    )


def _profile_catalog(snapshot: EnvySnapshot) -> ProfileCatalog:
    groups = tuple(
        ProfileGroup(group_id=group_id, name=name)
        for group_id, name in sorted(snapshot.profile_groups, key=lambda item: item[0])
    )
    profiles: list[Profile] = []
    for profile_id, name in sorted(snapshot.profiles, key=lambda item: item[0]):
        parsed = _parse_profile_id(profile_id, snapshot.active_profile_group)
        if parsed is None:
            continue
        group_id, index = parsed
        profiles.append(Profile(profile_id=profile_id, group_id=group_id, index=index, name=name))

    active_profiles = [ActiveProfile(group_id=group_id, index=str(index)) for group_id, index in snapshot.active_profiles]

    return ProfileCatalog(groups=groups, profiles=tuple(profiles), active_profiles=tuple(active_profiles))


def _parse_profile_id(profile_id: str, fallback_group: str | None) -> tuple[str, str] | None:
    for separator in ("_", ":"):
        group_id, found, raw_index = profile_id.rpartition(separator)
        if found and raw_index and group_id:
            if raw_index.startswith("profile") and raw_index.removeprefix("profile").isdigit():
                return group_id, raw_index.removeprefix("profile")
            return group_id, raw_index
    if profile_id.isdigit() and fallback_group:
        return fallback_group, profile_id
    return None
