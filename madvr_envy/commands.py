"""Typed command builders for madVR Envy IP control."""

from __future__ import annotations

from typing import Literal

from madvr_envy.protocol import build_command

MenuName = Literal["Info", "Settings", "Configuration", "Profiles", "TestPatterns"]
RemoteButton = Literal[
    "POWER",
    "INFO",
    "MENU",
    "LEFT",
    "RIGHT",
    "UP",
    "DOWN",
    "OK",
    "INPUT",
    "SETTINGS",
    "BACK",
    "RED",
    "GREEN",
    "BLUE",
    "YELLOW",
    "MAGENTA",
    "CYAN",
]
AspectRatioMode = Literal[
    "Auto",
    "Hold",
    "4:3",
    "16:9",
    "1.85:1",
    "2.00:1",
    "2.20:1",
    "2.35:1",
    "2.40:1",
    "2.55:1",
    "2.76:1",
]
OptionValue = str | int | bool


def _render_option_value(value: OptionValue) -> str | int:
    if isinstance(value, bool):
        return "YES" if value else "NO"
    return value


def heartbeat() -> str:
    return build_command("Heartbeat")


def bye() -> str:
    return build_command("Bye")


def power_off() -> str:
    return build_command("PowerOff")


def standby() -> str:
    return build_command("Standby")


def restart() -> str:
    return build_command("Restart")


def reload_software() -> str:
    return build_command("ReloadSoftware")


def open_menu(menu: MenuName | str) -> str:
    return build_command("OpenMenu", menu)


def close_menu() -> str:
    return build_command("CloseMenu")


def key_press(button: RemoteButton | str) -> str:
    return build_command("KeyPress", button)


def key_hold(button: RemoteButton | str) -> str:
    return build_command("KeyHold", button)


def display_alert_window(text: str) -> str:
    return build_command("DisplayAlertWindow", text)


def close_alert_window() -> str:
    return build_command("CloseAlertWindow")


def display_message(timeout_seconds: int, text: str) -> str:
    return build_command("DisplayMessage", timeout_seconds, text)


def display_audio_volume(min_value: int, current_value: int, max_value: int, unit_description: str) -> str:
    unit = unit_description if unit_description.startswith('"') and unit_description.endswith('"') else f'"{unit_description}"'
    return build_command("DisplayAudioVolume", min_value, current_value, max_value, unit)


def display_audio_mute() -> str:
    return build_command("DisplayAudioMute")


def close_audio_mute() -> str:
    return build_command("CloseAudioMute")


def set_aspect_ratio_mode(mode: AspectRatioMode | str) -> str:
    return build_command("SetAspectRatioMode", mode)


def get_incoming_signal_info() -> str:
    return build_command("GetIncomingSignalInfo")


def get_outgoing_signal_info() -> str:
    return build_command("GetOutgoingSignalInfo")


def get_aspect_ratio() -> str:
    return build_command("GetAspectRatio")


def get_masking_ratio() -> str:
    return build_command("GetMaskingRatio")


def get_temperatures() -> str:
    return build_command("GetTemperatures")


def get_mac_address() -> str:
    return build_command("GetMacAddress")


def create_profile_group(name: str) -> str:
    return build_command("CreateProfileGroup", name)


def rename_profile_group(group_id: str | int, name: str) -> str:
    return build_command("RenameProfileGroup", str(group_id), name)


def delete_profile_group(group_id: str | int) -> str:
    return build_command("DeleteProfileGroup", str(group_id))


def enum_profile_groups() -> str:
    return build_command("EnumProfileGroups")


def create_profile(profile_group: str | int, name: str) -> str:
    return build_command("CreateProfile", str(profile_group), name)


def rename_profile(profile_group: str | int, profile_id: int, name: str) -> str:
    return build_command("RenameProfile", str(profile_group), profile_id, name)


def delete_profile(profile_group: str | int, profile_id: int) -> str:
    return build_command("DeleteProfile", str(profile_group), profile_id)


def add_profile_to_page(full_profile_id: str, page_id: str) -> str:
    return build_command("AddProfileToPage", full_profile_id, page_id)


def remove_profile_from_page(full_profile_id: str, page_id: str) -> str:
    return build_command("RemoveProfileFromPage", full_profile_id, page_id)


def activate_profile(profile_group: str | int, profile_id: int) -> str:
    return build_command("ActivateProfile", str(profile_group), profile_id)


def get_active_profile(profile_group: str | int) -> str:
    return build_command("GetActiveProfile", str(profile_group))


def enum_profiles(profile_group: str | int) -> str:
    return build_command("EnumProfiles", str(profile_group))


def enum_setting_pages() -> str:
    return build_command("EnumSettingPages")


def enum_config_pages() -> str:
    return build_command("EnumConfigPages")


def enum_options(page_or_path: str) -> str:
    return build_command("EnumOptions", page_or_path)


def query_option(option_id_or_path: str) -> str:
    return build_command("QueryOption", option_id_or_path)


def change_option(option_id_path: str, value: OptionValue) -> str:
    return build_command("ChangeOption", option_id_path, _render_option_value(value))


def toggle_option(option_name: str) -> str:
    return build_command("Toggle", option_name)


def tone_map_on() -> str:
    return build_command("ToneMapOn")


def tone_map_off() -> str:
    return build_command("ToneMapOff")


def hotplug() -> str:
    return build_command("Hotplug")


def refresh_license_info() -> str:
    return build_command("RefreshLicenseInfo")


def force_1080p60_output() -> str:
    return build_command("Force1080p60Output")
