"""Canonical Envy state model."""

from __future__ import annotations

from dataclasses import dataclass, field

from madvr_envy.protocol import (
    ActivateProfileMessage,
    ActiveProfileMessage,
    AddProfileToPageMessage,
    AspectRatioMessage,
    ChangeOptionMessage,
    CloseMenuMessage,
    ConfigPageMessage,
    CreateProfileGroupMessage,
    CreateProfileMessage,
    Delete3DLUTFileMessage,
    DeleteProfileGroupMessage,
    DeleteProfileMessage,
    DisplayChangedMessage,
    FirmwareUpdateMessage,
    Force1080p60OutputMessage,
    HotplugMessage,
    IncomingSignalInfoMessage,
    InheritOptionMessage,
    KeyHoldMessage,
    KeyPressMessage,
    MacAddressMessage,
    MaskingRatioMessage,
    Message,
    MissingHeartbeatMessage,
    NoSignalMessage,
    OpenMenuMessage,
    OptionMessage,
    OutgoingSignalInfoMessage,
    PowerOffMessage,
    ProfileGroupMessage,
    ProfileMessage,
    RefreshLicenseInfoMessage,
    ReloadSoftwareMessage,
    RemoveProfileFromPageMessage,
    Rename3DLUTFileMessage,
    RenameProfileGroupMessage,
    RenameProfileMessage,
    ResetTemporaryMessage,
    RestartMessage,
    RestoreSettingsMessage,
    SetAspectRatioModeMessage,
    SettingPageMessage,
    StandbyMessage,
    StoreSettingsMessage,
    TemperaturesMessage,
    ToggleMessage,
    ToneMapOffMessage,
    ToneMapOnMessage,
    Upload3DLUTFileMessage,
    UploadSettingsFileMessage,
    WelcomeMessage,
)


@dataclass
class EnvyState:
    version: str | None = None
    is_on: bool | None = None
    standby: bool | None = None
    mac_address: str | None = None

    active_profile_group: str | None = None
    active_profile_index: int | None = None

    incoming_signal: IncomingSignalInfoMessage | None = None
    outgoing_signal: OutgoingSignalInfoMessage | None = None
    aspect_ratio: AspectRatioMessage | None = None
    masking_ratio: MaskingRatioMessage | None = None
    temperatures: TemperaturesMessage | None = None
    signal_present: bool | None = None
    current_menu: str | None = None
    aspect_ratio_mode: str | None = None
    last_button_event: tuple[str, str] | None = None
    settings_pages: dict[str, str] = field(default_factory=dict)
    config_pages: dict[str, str] = field(default_factory=dict)
    profile_groups: dict[str, str] = field(default_factory=dict)
    profiles: dict[str, str] = field(default_factory=dict)
    options: dict[str, OptionMessage] = field(default_factory=dict)
    tone_map_enabled: bool | None = None

    last_option_change: ChangeOptionMessage | None = None
    last_inherit_option: InheritOptionMessage | None = None
    last_uploaded_3dlut: str | None = None
    last_renamed_3dlut: tuple[str, str] | None = None
    last_deleted_3dlut: str | None = None
    settings_upload_count: int = 0
    last_store_settings: tuple[str, str] | None = None
    last_restore_settings: str | None = None
    temporary_reset_count: int = 0
    display_changed_count: int = 0
    firmware_update_pending: bool = False
    last_missing_heartbeat: bool = False
    last_system_action: str | None = None

    _seen_welcome: bool = False

    def reset_runtime_values(self) -> None:
        self.version = None
        self.is_on = None
        self.standby = None
        self.mac_address = None

        self.active_profile_group = None
        self.active_profile_index = None

        self.incoming_signal = None
        self.outgoing_signal = None
        self.aspect_ratio = None
        self.masking_ratio = None
        self.temperatures = None
        self.signal_present = None
        self.current_menu = None
        self.aspect_ratio_mode = None
        self.last_button_event = None
        self.settings_pages = {}
        self.config_pages = {}
        self.profile_groups = {}
        self.profiles = {}
        self.options = {}
        self.tone_map_enabled = None
        self.last_option_change = None
        self.last_inherit_option = None
        self.last_uploaded_3dlut = None
        self.last_renamed_3dlut = None
        self.last_deleted_3dlut = None
        self.settings_upload_count = 0
        self.last_store_settings = None
        self.last_restore_settings = None
        self.temporary_reset_count = 0
        self.display_changed_count = 0
        self.firmware_update_pending = False
        self.last_missing_heartbeat = False
        self.last_system_action = None

        self._seen_welcome = False

    def apply(self, message: Message) -> None:
        if isinstance(message, WelcomeMessage):
            self.version = message.version
            self._seen_welcome = True
            self.is_on = True
            self.standby = False
        elif isinstance(message, StandbyMessage):
            self.is_on = False
            self.standby = True
        elif isinstance(message, PowerOffMessage):
            self.is_on = False
            self.standby = False
        elif isinstance(message, RestartMessage):
            self.last_system_action = "Restart"
        elif isinstance(message, ReloadSoftwareMessage):
            self.last_system_action = "ReloadSoftware"
        elif isinstance(message, NoSignalMessage):
            self.signal_present = False
        elif isinstance(message, OpenMenuMessage):
            self.current_menu = message.menu
        elif isinstance(message, CloseMenuMessage):
            self.current_menu = None
        elif isinstance(message, KeyPressMessage):
            self.last_button_event = ("press", message.button)
        elif isinstance(message, KeyHoldMessage):
            self.last_button_event = ("hold", message.button)
        elif isinstance(message, SetAspectRatioModeMessage):
            self.aspect_ratio_mode = message.mode
        elif isinstance(message, MacAddressMessage):
            self.mac_address = message.mac
        elif isinstance(message, TemperaturesMessage):
            self.temperatures = message
        elif isinstance(message, IncomingSignalInfoMessage):
            self.incoming_signal = message
            self.signal_present = True
        elif isinstance(message, OutgoingSignalInfoMessage):
            self.outgoing_signal = message
        elif isinstance(message, AspectRatioMessage):
            self.aspect_ratio = message
        elif isinstance(message, MaskingRatioMessage):
            self.masking_ratio = message
        elif isinstance(message, (ActiveProfileMessage, ActivateProfileMessage)):
            self.active_profile_group = message.profile_group
            self.active_profile_index = message.profile_index
        elif isinstance(message, (CreateProfileGroupMessage, RenameProfileGroupMessage, ProfileGroupMessage)):
            self.profile_groups[message.group_id] = message.name
        elif isinstance(message, DeleteProfileGroupMessage):
            self.profile_groups.pop(message.group_id, None)
        elif isinstance(message, (CreateProfileMessage, RenameProfileMessage, ProfileMessage)):
            if isinstance(message, ProfileMessage):
                self.profiles[message.profile_id] = message.name
            else:
                key = f"{message.profile_group}_{message.profile_index}"
                self.profiles[key] = message.name
        elif isinstance(message, DeleteProfileMessage):
            key = f"{message.profile_group}_{message.profile_index}"
            self.profiles.pop(key, None)
        elif isinstance(message, SettingPageMessage):
            self.settings_pages[message.page_id] = message.name
        elif isinstance(message, ConfigPageMessage):
            self.config_pages[message.page_id] = message.name
        elif isinstance(message, OptionMessage):
            self.options[message.option_id] = message
        elif isinstance(message, ChangeOptionMessage):
            self.last_option_change = message
            self.options[message.option_id_path] = OptionMessage(
                option_type=message.option_type,
                option_id=message.option_id_path,
                current_value=message.current_value,
                effective_value=message.effective_value,
            )
        elif isinstance(message, InheritOptionMessage):
            self.last_inherit_option = message
        elif isinstance(message, ResetTemporaryMessage):
            self.temporary_reset_count += 1
        elif isinstance(message, Upload3DLUTFileMessage):
            self.last_uploaded_3dlut = message.filename
        elif isinstance(message, Rename3DLUTFileMessage):
            self.last_renamed_3dlut = (message.old_filename, message.new_filename)
        elif isinstance(message, Delete3DLUTFileMessage):
            self.last_deleted_3dlut = message.filename
        elif isinstance(message, UploadSettingsFileMessage):
            self.settings_upload_count += 1
        elif isinstance(message, StoreSettingsMessage):
            self.last_store_settings = (message.target, message.storage_name)
        elif isinstance(message, RestoreSettingsMessage):
            self.last_restore_settings = message.target
        elif isinstance(message, ToggleMessage):
            self.last_system_action = f"Toggle:{message.option}"
        elif isinstance(message, ToneMapOnMessage):
            self.tone_map_enabled = True
        elif isinstance(message, ToneMapOffMessage):
            self.tone_map_enabled = False
        elif isinstance(message, DisplayChangedMessage):
            self.display_changed_count += 1
        elif isinstance(message, RefreshLicenseInfoMessage):
            self.last_system_action = "RefreshLicenseInfo"
        elif isinstance(message, Force1080p60OutputMessage):
            self.last_system_action = "Force1080p60Output"
        elif isinstance(message, HotplugMessage):
            self.last_system_action = "Hotplug"
        elif isinstance(message, FirmwareUpdateMessage):
            self.firmware_update_pending = True
        elif isinstance(message, MissingHeartbeatMessage):
            self.last_missing_heartbeat = True
        elif isinstance(message, (AddProfileToPageMessage, RemoveProfileFromPageMessage)):
            self.last_system_action = message.__class__.__name__

    @property
    def synced(self) -> bool:
        return self._seen_welcome
