from pathlib import Path

from madvr_envy.protocol import UnknownMessage, parse_message
from madvr_envy.state import EnvyState


def _replay_fixture(name: str) -> tuple[EnvyState, list[str]]:
    fixture = Path(__file__).parent / "fixtures" / name
    lines = [line.strip() for line in fixture.read_text().splitlines() if line.strip()]

    state = EnvyState()
    unknown_lines: list[str] = []

    for line in lines:
        message = parse_message(line)
        if isinstance(message, UnknownMessage):
            unknown_lines.append(line)
        state.apply(message)

    return state, unknown_lines


def test_session_bootstrap_replay_converges_state():
    state, unknown_lines = _replay_fixture("session_bootstrap.log")

    assert unknown_lines == []
    assert state.synced is True
    assert state.version == "1.1.3"
    assert state.active_profile_group == "SOURCE"
    assert state.active_profile_index == 1
    assert state.current_menu is None
    assert state.signal_present is False
    assert state.mac_address == "01-02-03-04-05-06"
    assert state.temperatures is not None and state.temperatures.gpu == 74
    assert state.options["hdrHighlightRecovery"].current_value == 3
    assert state.last_inherit_option is not None and state.last_inherit_option.effective_value == 120
    assert state.temporary_reset_count == 1
    assert state.last_uploaded_3dlut == "BT.2020.3dlut"
    assert state.last_renamed_3dlut == ("BT.2020.3dlut", "BT.2021.3dlut")
    assert state.last_deleted_3dlut == "BT.2021.3dlut"
    assert state.settings_upload_count == 1
    assert state.last_store_settings == ("Installer", "Installer Settings")
    assert state.last_restore_settings == "Suggested"
    assert state.last_system_action == "Force1080p60Output"


def test_session_standby_wake_replay_converges_state():
    state, unknown_lines = _replay_fixture("session_standby_wake.log")

    assert unknown_lines == []
    assert state.synced is True
    assert state.version == "1.1.4"
    assert state.is_on is True
    assert state.standby is False
    assert state.current_menu is None
    assert state.active_profile_group == "SOURCE"
    assert state.active_profile_index == 2
    assert state.signal_present is False


def test_session_settings_churn_replay_converges_state():
    state, unknown_lines = _replay_fixture("session_settings_churn.log")

    assert unknown_lines == []
    assert state.synced is True
    assert state.options["hdrNits"].current_value == 120
    assert state.options["hdrNits"].effective_value == 120
    assert state.last_inherit_option is not None
    assert state.last_inherit_option.option_id_path == "temporary\\hdrNits"
    assert state.last_inherit_option.effective_value == 120
    assert state.temporary_reset_count == 1
    assert state.tone_map_enabled is False
    assert state.last_store_settings == ("1", "Slot 1 Fancy Name")
    assert state.last_restore_settings == "1"
