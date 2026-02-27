from madvr_envy import commands


def test_basic_command_builders():
    assert commands.heartbeat() == "Heartbeat"
    assert commands.power_off() == "PowerOff"
    assert commands.standby() == "Standby"
    assert commands.restart() == "Restart"
    assert commands.reload_software() == "ReloadSoftware"
    assert commands.bye() == "Bye"


def test_menu_and_key_commands():
    assert commands.open_menu("Configuration") == "OpenMenu Configuration"
    assert commands.close_menu() == "CloseMenu"
    assert commands.key_press("MENU") == "KeyPress MENU"
    assert commands.key_hold("DOWN") == "KeyHold DOWN"


def test_display_commands():
    assert commands.display_alert_window("Door bell is ringing!") == 'DisplayAlertWindow "Door bell is ringing!"'
    assert commands.display_message(3, "Hello world") == 'DisplayMessage 3 "Hello world"'
    assert commands.display_audio_volume(0, 60, 100, "%") == 'DisplayAudioVolume 0 60 100 "%"'
    assert commands.display_audio_mute() == "DisplayAudioMute"
    assert commands.close_audio_mute() == "CloseAudioMute"


def test_profile_and_option_commands():
    assert commands.activate_profile("SOURCE", 1) == "ActivateProfile SOURCE 1"
    assert commands.get_active_profile("SOURCE") == "GetActiveProfile SOURCE"
    assert commands.enum_profiles(1) == "EnumProfiles 1"
    assert commands.create_profile_group("Ambient Light") == 'CreateProfileGroup "Ambient Light"'
    assert commands.rename_profile_group(1, "Ambient Light 2") == 'RenameProfileGroup 1 "Ambient Light 2"'
    assert commands.change_option("temporary\\hdrNits", 121) == "ChangeOption temporary\\hdrNits 121"
    assert commands.change_option("someBooleanOpt", True) == "ChangeOption someBooleanOpt YES"
    assert commands.change_option("someBooleanOpt", False) == "ChangeOption someBooleanOpt NO"
    assert commands.tone_map_on() == "ToneMapOn"
    assert commands.tone_map_off() == "ToneMapOff"
