from madvr_envy.protocol import (
    ActiveProfileMessage,
    AspectRatioMessage,
    ChangeOptionMessage,
    ConfigPageMessage,
    CreateProfileGroupMessage,
    Delete3DLUTFileMessage,
    FirmwareUpdateMessage,
    IncomingSignalInfoMessage,
    KeyPressMessage,
    MacAddressMessage,
    NoSignalMessage,
    OpenMenuMessage,
    OptionMessage,
    PowerOffMessage,
    Rename3DLUTFileMessage,
    RestoreSettingsMessage,
    SettingPageMessage,
    StandbyMessage,
    StoreSettingsMessage,
    ToneMapOnMessage,
    Upload3DLUTFileMessage,
    UploadSettingsFileMessage,
    WelcomeMessage,
)
from madvr_envy.state import EnvyState


def test_state_sync_and_runtime_values():
    state = EnvyState()
    assert state.synced is False

    state.apply(WelcomeMessage(version="1.1.3"))
    assert state.synced is True
    assert state.is_on is True

    state.apply(MacAddressMessage(mac="01-02-03-04-05-06"))
    assert state.mac_address == "01-02-03-04-05-06"

    state.apply(StandbyMessage())
    assert state.is_on is False
    assert state.standby is True

    state.apply(PowerOffMessage())
    assert state.is_on is False
    assert state.standby is False


def test_signal_and_profile_updates():
    state = EnvyState()

    state.apply(
        IncomingSignalInfoMessage(
            resolution="3840x2160",
            frame_rate="23.976p",
            signal_type="2D",
            color_space="422",
            bit_depth="10bit",
            hdr_mode="HDR10",
            colorimetry="2020",
            black_levels="TV",
            aspect_ratio="16:9",
        )
    )
    assert state.signal_present is True
    assert state.incoming_signal is not None

    state.apply(NoSignalMessage())
    assert state.signal_present is False

    state.apply(ActiveProfileMessage(profile_group="SOURCE", profile_index=2))
    assert state.active_profile_group == "SOURCE"
    assert state.active_profile_index == 2

    state.apply(AspectRatioMessage(resolution="3840:1600", decimal_ratio=2.4, integer_ratio=240, name="Panavision"))
    assert state.aspect_ratio is not None
    assert state.aspect_ratio.name == "Panavision"


def test_extended_state_updates():
    state = EnvyState()
    state.reset_runtime_values()

    state.apply(OpenMenuMessage(menu="Settings"))
    assert state.current_menu == "Settings"

    state.apply(KeyPressMessage(button="MENU"))
    assert state.last_button_event == ("press", "MENU")

    state.apply(CreateProfileGroupMessage(group_id="customProfileGroup1", name="Ambient Light"))
    assert state.profile_groups == {"customProfileGroup1": "Ambient Light"}

    state.apply(SettingPageMessage(page_id="hdrSettings", name="HDR Settings"))
    state.apply(ConfigPageMessage(page_id="displayConfig", name="Display Config"))
    assert state.settings_pages is not None and state.settings_pages["hdrSettings"] == "HDR Settings"
    assert state.config_pages is not None and state.config_pages["displayConfig"] == "Display Config"

    state.apply(OptionMessage(option_type="INTEGER", option_id="hdrHighlightRecovery", current_value=2, effective_value=3))
    assert state.options is not None and state.options["hdrHighlightRecovery"].effective_value == 3

    state.apply(
        ChangeOptionMessage(
            option_type="INTEGER",
            option_id_path="temporary\\hdrNits",
            current_value=121,
            effective_value=121,
        )
    )
    assert state.last_option_change is not None
    assert state.options is not None and state.options["temporary\\hdrNits"].current_value == 121

    state.apply(ToneMapOnMessage())
    assert state.tone_map_enabled is True

    state.apply(FirmwareUpdateMessage())
    assert state.firmware_update_pending is True

    state.apply(Upload3DLUTFileMessage(filename="BT.2020.3dlut"))
    assert state.last_uploaded_3dlut == "BT.2020.3dlut"

    state.apply(Rename3DLUTFileMessage(old_filename="BT.2020.3dlut", new_filename="BT.2021.3dlut"))
    assert state.last_renamed_3dlut == ("BT.2020.3dlut", "BT.2021.3dlut")

    state.apply(Delete3DLUTFileMessage(filename="BT.2021.3dlut"))
    assert state.last_deleted_3dlut == "BT.2021.3dlut"

    state.apply(UploadSettingsFileMessage())
    assert state.settings_upload_count == 1

    state.apply(StoreSettingsMessage(target="Installer", storage_name="Installer Settings"))
    assert state.last_store_settings == ("Installer", "Installer Settings")

    state.apply(RestoreSettingsMessage(target="Suggested"))
    assert state.last_restore_settings == "Suggested"
