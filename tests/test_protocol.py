from madvr_envy.protocol import (
    ActiveProfileMessage,
    AspectRatioMessage,
    ChangeOptionMessage,
    ConfigPageEndMessage,
    ConfigPageMessage,
    CreateProfileGroupMessage,
    Delete3DLUTFileMessage,
    ErrorMessage,
    HotplugMessage,
    IncomingSignalInfoMessage,
    InheritOptionMessage,
    KeyPressMessage,
    MaskingRatioMessage,
    NoSignalMessage,
    OkMessage,
    OptionEndMessage,
    OptionMessage,
    OutgoingSignalInfoMessage,
    PowerOffMessage,
    ProfileEndMessage,
    ProfileGroupEndMessage,
    ProfileGroupMessage,
    ProfileMessage,
    Rename3DLUTFileMessage,
    ResetTemporaryMessage,
    RestoreSettingsMessage,
    SetAspectRatioModeMessage,
    SettingPageEndMessage,
    SettingPageMessage,
    StandbyMessage,
    StoreSettingsMessage,
    TemperaturesMessage,
    ToggleMessage,
    UnknownMessage,
    Upload3DLUTFileMessage,
    UploadSettingsFileMessage,
    WelcomeMessage,
    build_command,
    parse_message,
)


def test_parse_welcome_message():
    message = parse_message("WELCOME to Envy v1.0.1.0")
    assert isinstance(message, WelcomeMessage)
    assert message.version == "1.0.1.0"


def test_parse_ok_and_error_messages():
    assert isinstance(parse_message("OK"), OkMessage)
    error = parse_message('ERROR "invalid command"')
    assert isinstance(error, ErrorMessage)
    assert error.error == "invalid command"


def test_parse_state_notifications():
    assert isinstance(parse_message("Standby"), StandbyMessage)
    assert isinstance(parse_message("PowerOff"), PowerOffMessage)
    assert isinstance(parse_message("NoSignal"), NoSignalMessage)


def test_parse_incoming_and_outgoing_signal():
    incoming = parse_message("IncomingSignalInfo 3840x2160 23.976p 2D 422 10bit HDR10 2020 TV 16:9")
    assert isinstance(incoming, IncomingSignalInfoMessage)
    assert incoming.hdr_mode == "HDR10"
    assert incoming.aspect_ratio == "16:9"

    outgoing = parse_message("OutgoingSignalInfo 3840x2160 23.976p 2D RGB 12bit SDR 2020 TV")
    assert isinstance(outgoing, OutgoingSignalInfoMessage)
    assert outgoing.hdr_mode == "SDR"


def test_parse_aspect_and_masking_ratio():
    aspect = parse_message('AspectRatio 3840:1600 2.400 240 "Panavision 70"')
    assert isinstance(aspect, AspectRatioMessage)
    assert aspect.name == "Panavision 70"

    masking = parse_message("MaskingRatio 3840:1700 2.259 220")
    assert isinstance(masking, MaskingRatioMessage)
    assert masking.integer_ratio == 220


def test_parse_temperatures_allows_future_extra_values():
    message = parse_message("Temperatures 74 67 41 45 99")
    assert isinstance(message, TemperaturesMessage)
    assert message.gpu == 74
    assert message.extra == (99,)


def test_parse_profile_and_page_enumeration_messages():
    group = parse_message('ProfileGroup customProfileGroup1 "Ambient Light"')
    assert isinstance(group, ProfileGroupMessage)
    assert group.group_id == "customProfileGroup1"
    assert group.name == "Ambient Light"
    assert isinstance(parse_message("ProfileGroup."), ProfileGroupEndMessage)

    profile = parse_message('Profile sourceProfiles_profile2 "Panasonic Blu-Ray Player"')
    assert isinstance(profile, ProfileMessage)
    assert profile.profile_id == "sourceProfiles_profile2"
    assert isinstance(parse_message("Profile."), ProfileEndMessage)

    setting_page = parse_message('SettingPage hdrSettings "hdr settings"')
    assert isinstance(setting_page, SettingPageMessage)
    assert setting_page.page_id == "hdrSettings"
    assert isinstance(parse_message("SettingPage."), SettingPageEndMessage)

    config_page = parse_message('ConfigPage displayConfig "display config"')
    assert isinstance(config_page, ConfigPageMessage)
    assert config_page.page_id == "displayConfig"
    assert isinstance(parse_message("ConfigPage."), ConfigPageEndMessage)


def test_parse_option_messages():
    option = parse_message('Option STRING hdrMode "toneMapMath" "toneMapMath"')
    assert isinstance(option, OptionMessage)
    assert option.option_id == "hdrMode"
    assert option.current_value == "toneMapMath"
    assert isinstance(parse_message("Option."), OptionEndMessage)

    changed = parse_message("ChangeOption INTEGER hdrHighlightRecovery 2 3")
    assert isinstance(changed, ChangeOptionMessage)
    assert changed.option_type == "INTEGER"
    assert changed.option_id_path == "hdrHighlightRecovery"
    assert changed.current_value == 2
    assert changed.effective_value == 3

    inherited = parse_message("InheritOption INTEGER temporary\\hdrNits 120")
    assert isinstance(inherited, InheritOptionMessage)
    assert inherited.option_id_path == "temporary\\hdrNits"
    assert inherited.effective_value == 120

    assert isinstance(parse_message("ResetTemporary"), ResetTemporaryMessage)


def test_parse_option_scalar_types():
    int_opt = parse_message("Option INTEGER hdrNits 120 121")
    assert isinstance(int_opt, OptionMessage)
    assert int_opt.current_value == 120
    assert int_opt.effective_value == 121

    float_opt = parse_message("Option FLOAT someFloat 1.25 2.50")
    assert isinstance(float_opt, OptionMessage)
    assert float_opt.current_value == 1.25
    assert float_opt.effective_value == 2.5

    bool_opt = parse_message("Option BOOLEAN someBool YES NO")
    assert isinstance(bool_opt, OptionMessage)
    assert bool_opt.current_value is True
    assert bool_opt.effective_value is False


def test_parse_misc_notifications():
    assert isinstance(parse_message("ActiveProfile SOURCE 2"), ActiveProfileMessage)

    key = parse_message("KeyPress MENU")
    assert isinstance(key, KeyPressMessage)
    assert key.button == "MENU"

    aspect_mode = parse_message("SetAspectRatioMode Auto")
    assert isinstance(aspect_mode, SetAspectRatioModeMessage)
    assert aspect_mode.mode == "Auto"

    created = parse_message('CreateProfileGroup 1 "Ambient Light"')
    assert isinstance(created, CreateProfileGroupMessage)
    assert created.group_id == "1"

    toggle = parse_message("Toggle ToneMap")
    assert isinstance(toggle, ToggleMessage)
    assert toggle.option == "ToneMap"

    assert isinstance(parse_message("Hotplug"), HotplugMessage)


def test_parse_3dlut_and_settings_notifications():
    upload_lut = parse_message('Upload3DLUTFile "BT.2020.3dlut"')
    assert isinstance(upload_lut, Upload3DLUTFileMessage)
    assert upload_lut.filename == "BT.2020.3dlut"

    rename_lut = parse_message('Rename3DLUTFile "BT.2020.3dlut" "BT.2021.3dlut"')
    assert isinstance(rename_lut, Rename3DLUTFileMessage)
    assert rename_lut.old_filename == "BT.2020.3dlut"
    assert rename_lut.new_filename == "BT.2021.3dlut"

    delete_lut = parse_message('Delete3DLUTFile "BT.2021.3dlut"')
    assert isinstance(delete_lut, Delete3DLUTFileMessage)
    assert delete_lut.filename == "BT.2021.3dlut"

    assert isinstance(parse_message("UploadSettingsFile"), UploadSettingsFileMessage)

    store = parse_message('StoreSettings Installer "Installer Settings"')
    assert isinstance(store, StoreSettingsMessage)
    assert store.target == "Installer"
    assert store.storage_name == "Installer Settings"

    restore = parse_message("RestoreSettings Suggested")
    assert isinstance(restore, RestoreSettingsMessage)
    assert restore.target == "Suggested"


def test_parser_returns_unknown_for_unhandled_lines():
    message = parse_message("UnrecognizedMessage 123")
    assert isinstance(message, UnknownMessage)
    assert message.raw.startswith("UnrecognizedMessage")


def test_build_command_quotes_only_when_needed():
    assert build_command("GetMacAddress") == "GetMacAddress"
    assert build_command("DisplayMessage", 3, "Hello world") == 'DisplayMessage 3 "Hello world"'
    assert build_command("ChangeOption", "temporary\\hdrNits", 121) == "ChangeOption temporary\\hdrNits 121"
