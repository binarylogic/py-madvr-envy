from __future__ import annotations

from types import SimpleNamespace

import pytest

from madvr_envy.integration_bridge import (
    action_names,
    build_profile_options,
    iter_remote_operations,
    normalize_action,
    parse_profile_id,
    resolve_action_method,
)


def test_action_names_sorted():
    assert action_names() == (
        "hotplug",
        "power_off",
        "reload_software",
        "restart",
        "standby",
        "tone_map_off",
        "tone_map_on",
    )


def test_normalize_action_and_resolve_method():
    called = []

    async def restart():
        called.append("restart")

    client = SimpleNamespace(restart=restart)
    method = resolve_action_method(client, " Restart ")
    assert method is restart


def test_normalize_action_invalid():
    with pytest.raises(ValueError):
        normalize_action("unknown_action")


def test_iter_remote_operations():
    ops = iter_remote_operations([" MENU ", "action:restart", "", 123, "action: "])
    assert [(op.kind, op.value) for op in ops] == [
        ("key", "MENU"),
        ("action", "restart"),
    ]


def test_parse_profile_id():
    assert parse_profile_id("1_2", None) == ("1", 2)
    assert parse_profile_id("source:5", None) == ("source", 5)
    assert parse_profile_id("7", "fallback") == ("fallback", 7)
    assert parse_profile_id("bad-value", "fallback") is None


def test_build_profile_options():
    data = {
        "profile_groups": {"1": "Cinema", "2": "Sports"},
        "profiles": {"1_2": "Night", "1_1": "Day", "2_1": "Game"},
        "active_profile_group": "1",
    }
    options = build_profile_options(data)
    assert [option.option for option in options] == [
        "Cinema: Day",
        "Cinema: Night",
        "Sports: Game",
    ]
    assert [(option.group_id, option.profile_index) for option in options] == [
        ("1", 1),
        ("1", 2),
        ("2", 1),
    ]
