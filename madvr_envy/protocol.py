"""Protocol models and parser for madVR Envy IP Control."""

from __future__ import annotations

import re
from dataclasses import dataclass

OptionScalar = str | int | float | bool


@dataclass(frozen=True)
class Message:
    """Base protocol message."""


@dataclass(frozen=True)
class WelcomeMessage(Message):
    version: str


@dataclass(frozen=True)
class OkMessage(Message):
    pass


@dataclass(frozen=True)
class ErrorMessage(Message):
    error: str


@dataclass(frozen=True)
class StandbyMessage(Message):
    pass


@dataclass(frozen=True)
class PowerOffMessage(Message):
    pass


@dataclass(frozen=True)
class RestartMessage(Message):
    pass


@dataclass(frozen=True)
class ReloadSoftwareMessage(Message):
    pass


@dataclass(frozen=True)
class NoSignalMessage(Message):
    pass


@dataclass(frozen=True)
class OpenMenuMessage(Message):
    menu: str


@dataclass(frozen=True)
class CloseMenuMessage(Message):
    pass


@dataclass(frozen=True)
class KeyPressMessage(Message):
    button: str


@dataclass(frozen=True)
class KeyHoldMessage(Message):
    button: str


@dataclass(frozen=True)
class SetAspectRatioModeMessage(Message):
    mode: str


@dataclass(frozen=True)
class ActivateProfileMessage(Message):
    profile_group: str
    profile_index: int


@dataclass(frozen=True)
class ActiveProfileMessage(Message):
    profile_group: str
    profile_index: int


@dataclass(frozen=True)
class CreateProfileGroupMessage(Message):
    group_id: str
    name: str


@dataclass(frozen=True)
class RenameProfileGroupMessage(Message):
    group_id: str
    name: str


@dataclass(frozen=True)
class DeleteProfileGroupMessage(Message):
    group_id: str


@dataclass(frozen=True)
class CreateProfileMessage(Message):
    profile_group: str
    profile_index: int
    name: str


@dataclass(frozen=True)
class RenameProfileMessage(Message):
    profile_group: str
    profile_index: int
    name: str


@dataclass(frozen=True)
class DeleteProfileMessage(Message):
    profile_group: str
    profile_index: int


@dataclass(frozen=True)
class AddProfileToPageMessage(Message):
    profile_id: str
    page_id: str


@dataclass(frozen=True)
class RemoveProfileFromPageMessage(Message):
    profile_id: str
    page_id: str


@dataclass(frozen=True)
class IncomingSignalInfoMessage(Message):
    resolution: str
    frame_rate: str
    signal_type: str
    color_space: str
    bit_depth: str
    hdr_mode: str
    colorimetry: str
    black_levels: str
    aspect_ratio: str


@dataclass(frozen=True)
class OutgoingSignalInfoMessage(Message):
    resolution: str
    frame_rate: str
    signal_type: str
    color_space: str
    bit_depth: str
    hdr_mode: str
    colorimetry: str
    black_levels: str


@dataclass(frozen=True)
class AspectRatioMessage(Message):
    resolution: str
    decimal_ratio: float
    integer_ratio: int
    name: str


@dataclass(frozen=True)
class MaskingRatioMessage(Message):
    resolution: str
    decimal_ratio: float
    integer_ratio: int


@dataclass(frozen=True)
class TemperaturesMessage(Message):
    gpu: int
    hdmi_input: int
    cpu: int
    mainboard: int
    extra: tuple[int, ...]


@dataclass(frozen=True)
class MacAddressMessage(Message):
    mac: str


@dataclass(frozen=True)
class ProfileGroupMessage(Message):
    group_id: str
    name: str


@dataclass(frozen=True)
class ProfileGroupEndMessage(Message):
    pass


@dataclass(frozen=True)
class ProfileMessage(Message):
    profile_id: str
    name: str


@dataclass(frozen=True)
class ProfileEndMessage(Message):
    pass


@dataclass(frozen=True)
class SettingPageMessage(Message):
    page_id: str
    name: str


@dataclass(frozen=True)
class SettingPageEndMessage(Message):
    pass


@dataclass(frozen=True)
class ConfigPageMessage(Message):
    page_id: str
    name: str


@dataclass(frozen=True)
class ConfigPageEndMessage(Message):
    pass


@dataclass(frozen=True)
class OptionMessage(Message):
    option_type: str
    option_id: str
    current_value: OptionScalar
    effective_value: OptionScalar


@dataclass(frozen=True)
class OptionEndMessage(Message):
    pass


@dataclass(frozen=True)
class ChangeOptionMessage(Message):
    option_type: str
    option_id_path: str
    current_value: OptionScalar
    effective_value: OptionScalar


@dataclass(frozen=True)
class InheritOptionMessage(Message):
    option_type: str
    option_id_path: str
    effective_value: OptionScalar


@dataclass(frozen=True)
class ResetTemporaryMessage(Message):
    pass


@dataclass(frozen=True)
class Upload3DLUTFileMessage(Message):
    filename: str


@dataclass(frozen=True)
class Rename3DLUTFileMessage(Message):
    old_filename: str
    new_filename: str


@dataclass(frozen=True)
class Delete3DLUTFileMessage(Message):
    filename: str


@dataclass(frozen=True)
class UploadSettingsFileMessage(Message):
    pass


@dataclass(frozen=True)
class StoreSettingsMessage(Message):
    target: str
    storage_name: str


@dataclass(frozen=True)
class RestoreSettingsMessage(Message):
    target: str


@dataclass(frozen=True)
class ToggleMessage(Message):
    option: str


@dataclass(frozen=True)
class ToneMapOnMessage(Message):
    pass


@dataclass(frozen=True)
class ToneMapOffMessage(Message):
    pass


@dataclass(frozen=True)
class DisplayChangedMessage(Message):
    pass


@dataclass(frozen=True)
class RefreshLicenseInfoMessage(Message):
    pass


@dataclass(frozen=True)
class Force1080p60OutputMessage(Message):
    pass


@dataclass(frozen=True)
class HotplugMessage(Message):
    pass


@dataclass(frozen=True)
class FirmwareUpdateMessage(Message):
    pass


@dataclass(frozen=True)
class MissingHeartbeatMessage(Message):
    pass


@dataclass(frozen=True)
class UnknownMessage(Message):
    raw: str


TOKEN_PATTERN = re.compile(r'"[^"]*"|\S+')


def _tokens(line: str) -> list[str]:
    return [token for token in TOKEN_PATTERN.findall(line)]


def _unquote(token: str) -> str:
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        return token[1:-1]
    return token


def _to_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _parse_option_scalar(option_type: str, value: str) -> OptionScalar:
    raw = _unquote(value)
    normalized_type = option_type.upper()

    if normalized_type in {"INTEGER", "INT"}:
        parsed = _to_int(raw)
        if parsed is not None:
            return parsed
    elif normalized_type in {"FLOAT", "DOUBLE"}:
        try:
            return float(raw)
        except ValueError:
            return raw
    elif normalized_type in {"BOOLEAN", "BOOL"}:
        upper = raw.upper()
        if upper in {"YES", "TRUE", "ON"}:
            return True
        if upper in {"NO", "FALSE", "OFF"}:
            return False

    return raw


def _parse_welcome(line: str) -> Message:
    match = re.match(r"^WELCOME to Envy v([^\s]+)$", line)
    if match is None:
        return UnknownMessage(line)
    return WelcomeMessage(version=match.group(1))


def _parse_error(line: str) -> Message:
    match = re.match(r'^ERROR\s+"?(.*?)"?$', line)
    if match is None:
        return UnknownMessage(line)
    return ErrorMessage(error=match.group(1))


def _parse_open_menu(tokens: list[str], line: str) -> Message:
    if len(tokens) != 2:
        return UnknownMessage(line)
    return OpenMenuMessage(menu=_unquote(tokens[1]))


def _parse_key(tokens: list[str], line: str) -> Message:
    if len(tokens) != 2:
        return UnknownMessage(line)
    if tokens[0] == "KeyPress":
        return KeyPressMessage(button=tokens[1])
    return KeyHoldMessage(button=tokens[1])


def _parse_set_aspect_ratio_mode(tokens: list[str], line: str) -> Message:
    if len(tokens) != 2:
        return UnknownMessage(line)
    return SetAspectRatioModeMessage(mode=tokens[1])


def _parse_activate_profile(tokens: list[str], line: str) -> Message:
    if len(tokens) != 3:
        return UnknownMessage(line)
    index = _to_int(tokens[2])
    if index is None:
        return UnknownMessage(line)
    return ActivateProfileMessage(profile_group=tokens[1], profile_index=index)


def _parse_active_profile(tokens: list[str], line: str) -> Message:
    if len(tokens) != 3:
        return UnknownMessage(line)
    index = _to_int(tokens[2])
    if index is None:
        return UnknownMessage(line)
    return ActiveProfileMessage(profile_group=tokens[1], profile_index=index)


def _parse_create_profile_group(tokens: list[str], line: str) -> Message:
    if len(tokens) < 3:
        return UnknownMessage(line)
    return CreateProfileGroupMessage(group_id=tokens[1], name=_unquote(" ".join(tokens[2:])))


def _parse_rename_profile_group(tokens: list[str], line: str) -> Message:
    if len(tokens) < 3:
        return UnknownMessage(line)
    return RenameProfileGroupMessage(group_id=tokens[1], name=_unquote(" ".join(tokens[2:])))


def _parse_delete_profile_group(tokens: list[str], line: str) -> Message:
    if len(tokens) != 2:
        return UnknownMessage(line)
    return DeleteProfileGroupMessage(group_id=tokens[1])


def _parse_profile_change(tokens: list[str], line: str) -> Message:
    if len(tokens) < 3:
        return UnknownMessage(line)
    profile_index = _to_int(tokens[2])
    if profile_index is None:
        return UnknownMessage(line)

    if tokens[0] == "DeleteProfile":
        return DeleteProfileMessage(profile_group=tokens[1], profile_index=profile_index)

    if len(tokens) < 4:
        return UnknownMessage(line)
    name = _unquote(" ".join(tokens[3:]))
    if tokens[0] == "CreateProfile":
        return CreateProfileMessage(profile_group=tokens[1], profile_index=profile_index, name=name)
    return RenameProfileMessage(profile_group=tokens[1], profile_index=profile_index, name=name)


def _parse_profile_page_link(tokens: list[str], line: str) -> Message:
    if len(tokens) != 3:
        return UnknownMessage(line)
    if tokens[0] == "AddProfileToPage":
        return AddProfileToPageMessage(profile_id=tokens[1], page_id=tokens[2])
    return RemoveProfileFromPageMessage(profile_id=tokens[1], page_id=tokens[2])


def _parse_incoming_signal(tokens: list[str], line: str) -> Message:
    if len(tokens) < 10:
        return UnknownMessage(line)
    return IncomingSignalInfoMessage(
        resolution=tokens[1],
        frame_rate=tokens[2],
        signal_type=tokens[3],
        color_space=tokens[4],
        bit_depth=tokens[5],
        hdr_mode=tokens[6],
        colorimetry=tokens[7],
        black_levels=tokens[8],
        aspect_ratio=tokens[9],
    )


def _parse_outgoing_signal(tokens: list[str], line: str) -> Message:
    if len(tokens) < 9:
        return UnknownMessage(line)
    return OutgoingSignalInfoMessage(
        resolution=tokens[1],
        frame_rate=tokens[2],
        signal_type=tokens[3],
        color_space=tokens[4],
        bit_depth=tokens[5],
        hdr_mode=tokens[6],
        colorimetry=tokens[7],
        black_levels=tokens[8],
    )


def _parse_aspect_ratio(tokens: list[str], line: str) -> Message:
    if len(tokens) < 5:
        return UnknownMessage(line)
    decimal_ratio = float(tokens[2])
    integer_ratio = _to_int(tokens[3])
    if integer_ratio is None:
        return UnknownMessage(line)
    return AspectRatioMessage(
        resolution=tokens[1],
        decimal_ratio=decimal_ratio,
        integer_ratio=integer_ratio,
        name=_unquote(" ".join(tokens[4:])),
    )


def _parse_masking_ratio(tokens: list[str], line: str) -> Message:
    if len(tokens) != 4:
        return UnknownMessage(line)
    integer_ratio = _to_int(tokens[3])
    if integer_ratio is None:
        return UnknownMessage(line)
    return MaskingRatioMessage(
        resolution=tokens[1],
        decimal_ratio=float(tokens[2]),
        integer_ratio=integer_ratio,
    )


def _parse_temperatures(tokens: list[str], line: str) -> Message:
    if len(tokens) < 5:
        return UnknownMessage(line)
    values = [_to_int(token) for token in tokens[1:]]
    if any(value is None for value in values):
        return UnknownMessage(line)
    safe_values = [value for value in values if value is not None]
    return TemperaturesMessage(
        gpu=safe_values[0],
        hdmi_input=safe_values[1],
        cpu=safe_values[2],
        mainboard=safe_values[3],
        extra=tuple(safe_values[4:]),
    )


def _parse_mac(tokens: list[str], line: str) -> Message:
    if len(tokens) != 2:
        return UnknownMessage(line)
    if re.match(r"^[0-9A-Fa-f:-]{17}$", tokens[1]) is None:
        return UnknownMessage(line)
    return MacAddressMessage(mac=tokens[1])


def _parse_profile_group(tokens: list[str], line: str) -> Message:
    if len(tokens) == 1 and tokens[0] == "ProfileGroup.":
        return ProfileGroupEndMessage()
    if len(tokens) < 3:
        return UnknownMessage(line)
    return ProfileGroupMessage(group_id=tokens[1], name=_unquote(" ".join(tokens[2:])))


def _parse_profile(tokens: list[str], line: str) -> Message:
    if len(tokens) == 1 and tokens[0] == "Profile.":
        return ProfileEndMessage()
    if len(tokens) < 3:
        return UnknownMessage(line)
    return ProfileMessage(profile_id=tokens[1], name=_unquote(" ".join(tokens[2:])))


def _parse_setting_page(tokens: list[str], line: str) -> Message:
    if len(tokens) == 1 and tokens[0] == "SettingPage.":
        return SettingPageEndMessage()
    if len(tokens) < 3:
        return UnknownMessage(line)
    return SettingPageMessage(page_id=tokens[1], name=_unquote(" ".join(tokens[2:])))


def _parse_config_page(tokens: list[str], line: str) -> Message:
    if len(tokens) == 1 and tokens[0] == "ConfigPage.":
        return ConfigPageEndMessage()
    if len(tokens) < 3:
        return UnknownMessage(line)
    return ConfigPageMessage(page_id=tokens[1], name=_unquote(" ".join(tokens[2:])))


def _parse_option(tokens: list[str], line: str) -> Message:
    if len(tokens) == 1 and tokens[0] == "Option.":
        return OptionEndMessage()
    if len(tokens) != 5:
        return UnknownMessage(line)
    return OptionMessage(
        option_type=tokens[1],
        option_id=tokens[2],
        current_value=_parse_option_scalar(tokens[1], tokens[3]),
        effective_value=_parse_option_scalar(tokens[1], tokens[4]),
    )


def _parse_change_option(tokens: list[str], line: str) -> Message:
    if len(tokens) != 5:
        return UnknownMessage(line)
    return ChangeOptionMessage(
        option_type=tokens[1],
        option_id_path=tokens[2],
        current_value=_parse_option_scalar(tokens[1], tokens[3]),
        effective_value=_parse_option_scalar(tokens[1], tokens[4]),
    )


def _parse_inherit_option(tokens: list[str], line: str) -> Message:
    if len(tokens) != 4:
        return UnknownMessage(line)
    return InheritOptionMessage(
        option_type=tokens[1],
        option_id_path=tokens[2],
        effective_value=_parse_option_scalar(tokens[1], tokens[3]),
    )


def _parse_upload_3dlut_file(tokens: list[str], line: str) -> Message:
    if len(tokens) < 2:
        return UnknownMessage(line)
    return Upload3DLUTFileMessage(filename=_unquote(" ".join(tokens[1:])))


def _parse_rename_3dlut_file(tokens: list[str], line: str) -> Message:
    if len(tokens) != 3:
        return UnknownMessage(line)
    return Rename3DLUTFileMessage(old_filename=_unquote(tokens[1]), new_filename=_unquote(tokens[2]))


def _parse_delete_3dlut_file(tokens: list[str], line: str) -> Message:
    if len(tokens) < 2:
        return UnknownMessage(line)
    return Delete3DLUTFileMessage(filename=_unquote(" ".join(tokens[1:])))


def _parse_store_settings(tokens: list[str], line: str) -> Message:
    if len(tokens) < 3:
        return UnknownMessage(line)
    return StoreSettingsMessage(target=tokens[1], storage_name=_unquote(" ".join(tokens[2:])))


def _parse_restore_settings(tokens: list[str], line: str) -> Message:
    if len(tokens) != 2:
        return UnknownMessage(line)
    return RestoreSettingsMessage(target=tokens[1])


def parse_message(line: str) -> Message:
    """Parse one line from the Envy stream."""
    normalized = line.strip()
    if normalized == "":
        return UnknownMessage(line)
    tokens = _tokens(normalized)
    head = tokens[0]

    try:
        if normalized.startswith("WELCOME to Envy v"):
            return _parse_welcome(normalized)
        if head == "OK":
            return OkMessage()
        if head == "ERROR":
            return _parse_error(normalized)
        if head == "Standby":
            return StandbyMessage()
        if head == "PowerOff":
            return PowerOffMessage()
        if head == "Restart":
            return RestartMessage()
        if head == "ReloadSoftware":
            return ReloadSoftwareMessage()
        if head == "NoSignal":
            return NoSignalMessage()
        if head == "OpenMenu":
            return _parse_open_menu(tokens, normalized)
        if head == "CloseMenu":
            return CloseMenuMessage()
        if head in {"KeyPress", "KeyHold"}:
            return _parse_key(tokens, normalized)
        if head == "SetAspectRatioMode":
            return _parse_set_aspect_ratio_mode(tokens, normalized)
        if head == "ActivateProfile":
            return _parse_activate_profile(tokens, normalized)
        if head == "ActiveProfile":
            return _parse_active_profile(tokens, normalized)
        if head == "CreateProfileGroup":
            return _parse_create_profile_group(tokens, normalized)
        if head == "RenameProfileGroup":
            return _parse_rename_profile_group(tokens, normalized)
        if head == "DeleteProfileGroup":
            return _parse_delete_profile_group(tokens, normalized)
        if head in {"CreateProfile", "RenameProfile", "DeleteProfile"}:
            return _parse_profile_change(tokens, normalized)
        if head in {"AddProfileToPage", "RemoveProfileFromPage"}:
            return _parse_profile_page_link(tokens, normalized)
        if head == "IncomingSignalInfo":
            return _parse_incoming_signal(tokens, normalized)
        if head == "OutgoingSignalInfo":
            return _parse_outgoing_signal(tokens, normalized)
        if head == "AspectRatio":
            return _parse_aspect_ratio(tokens, normalized)
        if head == "MaskingRatio":
            return _parse_masking_ratio(tokens, normalized)
        if head == "Temperatures":
            return _parse_temperatures(tokens, normalized)
        if head == "MacAddress":
            return _parse_mac(tokens, normalized)
        if head.startswith("ProfileGroup"):
            return _parse_profile_group(tokens, normalized)
        if head.startswith("Profile"):
            return _parse_profile(tokens, normalized)
        if head.startswith("SettingPage"):
            return _parse_setting_page(tokens, normalized)
        if head.startswith("ConfigPage"):
            return _parse_config_page(tokens, normalized)
        if head.startswith("Option"):
            return _parse_option(tokens, normalized)
        if head == "ChangeOption":
            return _parse_change_option(tokens, normalized)
        if head == "InheritOption":
            return _parse_inherit_option(tokens, normalized)
        if head == "ResetTemporary":
            return ResetTemporaryMessage()
        if head == "Upload3DLUTFile":
            return _parse_upload_3dlut_file(tokens, normalized)
        if head == "Rename3DLUTFile":
            return _parse_rename_3dlut_file(tokens, normalized)
        if head == "Delete3DLUTFile":
            return _parse_delete_3dlut_file(tokens, normalized)
        if head == "UploadSettingsFile":
            return UploadSettingsFileMessage()
        if head == "StoreSettings":
            return _parse_store_settings(tokens, normalized)
        if head == "RestoreSettings":
            return _parse_restore_settings(tokens, normalized)
        if head == "Toggle" and len(tokens) == 2:
            return ToggleMessage(option=tokens[1])
        if head == "ToneMapOn":
            return ToneMapOnMessage()
        if head == "ToneMapOff":
            return ToneMapOffMessage()
        if head == "DisplayChanged":
            return DisplayChangedMessage()
        if head == "RefreshLicenseInfo":
            return RefreshLicenseInfoMessage()
        if head == "Force1080p60Output":
            return Force1080p60OutputMessage()
        if head == "Hotplug":
            return HotplugMessage()
        if head == "FirmwareUpdate":
            return FirmwareUpdateMessage()
        if head == "MissingHeartbeat":
            return MissingHeartbeatMessage()
    except (ValueError, IndexError):
        return UnknownMessage(line)

    return UnknownMessage(line)


def quote_if_needed(value: str) -> str:
    """Quote command parameter only when required by protocol syntax."""
    if " " in value and not (value.startswith('"') and value.endswith('"')):
        return f'"{value}"'
    return value


def build_command(command: str, *args: str | int) -> str:
    """Build one protocol command line without CRLF."""
    rendered: list[str] = [command]
    for arg in args:
        if isinstance(arg, int):
            rendered.append(str(arg))
        else:
            rendered.append(quote_if_needed(arg))
    return " ".join(rendered)
