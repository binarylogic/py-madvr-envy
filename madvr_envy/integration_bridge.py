"""Shared helpers for Home Assistant-style madVR Envy integrations."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

_PROFILE_ID_RE = re.compile(r"^(?P<group>.+?)[_:](?P<index>\d+)$")


class EnvyAction(StrEnum):
    """Named action commands supported by the integration."""

    STANDBY = "standby"
    POWER_OFF = "power_off"
    HOTPLUG = "hotplug"
    RESTART = "restart"
    RELOAD_SOFTWARE = "reload_software"
    TONE_MAP_ON = "tone_map_on"
    TONE_MAP_OFF = "tone_map_off"


ACTION_METHODS: dict[EnvyAction, str] = {
    EnvyAction.STANDBY: "standby",
    EnvyAction.POWER_OFF: "power_off",
    EnvyAction.HOTPLUG: "hotplug",
    EnvyAction.RESTART: "restart",
    EnvyAction.RELOAD_SOFTWARE: "reload_software",
    EnvyAction.TONE_MAP_ON: "tone_map_on",
    EnvyAction.TONE_MAP_OFF: "tone_map_off",
}


@dataclass(frozen=True, slots=True)
class ProfileOption:
    """Profile option label and target selection."""

    option: str
    group_id: str
    profile_index: int


@dataclass(frozen=True, slots=True)
class RemoteOperation:
    """One normalized remote operation."""

    kind: str
    value: str


def action_names() -> tuple[str, ...]:
    """Return sorted action names for validation/selectors."""
    return tuple(sorted(action.value for action in EnvyAction))


def normalize_action(action: str) -> EnvyAction:
    """Parse and validate action string."""
    return EnvyAction(action.strip().lower())


def resolve_action_method(client: Any, action: str | EnvyAction) -> Callable[[], Awaitable[Any]]:
    """Resolve one action to a bound client command method."""
    action_name = normalize_action(action.value if isinstance(action, EnvyAction) else action)
    method_name = ACTION_METHODS[action_name]
    method = getattr(client, method_name)
    return method


def iter_remote_operations(command: str | Iterable[object]) -> tuple[RemoteOperation, ...]:
    """Normalize remote command payloads to key/action operations."""
    raw_values = [command] if isinstance(command, str) else list(command)
    ops: list[RemoteOperation] = []
    for raw in raw_values:
        if not isinstance(raw, str):
            continue
        token = raw.strip()
        if not token:
            continue
        if token.startswith("action:"):
            action = token.split(":", 1)[1].strip()
            if not action:
                continue
            ops.append(RemoteOperation(kind="action", value=action))
            continue
        ops.append(RemoteOperation(kind="key", value=token))
    return tuple(ops)


def parse_profile_id(profile_id: str, fallback_group: object) -> tuple[str, int] | None:
    """Parse profile identifier into group/index."""
    matched = _PROFILE_ID_RE.match(profile_id)
    if matched is not None:
        return matched.group("group"), int(matched.group("index"))

    if profile_id.isdigit() and isinstance(fallback_group, str):
        return fallback_group, int(profile_id)

    return None


def build_profile_options(data: Mapping[str, object]) -> list[ProfileOption]:
    """Build sorted profile selection options from adapter payload."""
    group_names = data.get("profile_groups")
    if not isinstance(group_names, Mapping):
        group_names = {}

    profiles = data.get("profiles")
    if not isinstance(profiles, Mapping):
        return []

    options: list[ProfileOption] = []
    for profile_id, profile_name in profiles.items():
        if not isinstance(profile_id, str) or not isinstance(profile_name, str):
            continue

        parsed = parse_profile_id(profile_id, data.get("active_profile_group"))
        if parsed is None:
            continue
        group_id, index = parsed

        group_label = group_names.get(group_id, group_id)
        if not isinstance(group_label, str):
            group_label = group_id

        options.append(
            ProfileOption(
                option=f"{group_label}: {profile_name}",
                group_id=group_id,
                profile_index=index,
            )
        )

    options.sort(key=lambda option: option.option.casefold())
    return options
