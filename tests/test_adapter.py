from madvr_envy.adapter import EnvyStateAdapter, snapshot_from_state
from madvr_envy.protocol import (
    ChangeOptionMessage,
    DisplayChangedMessage,
    IncomingSignalInfoMessage,
    KeyPressMessage,
    ResetTemporaryMessage,
    StoreSettingsMessage,
    ToneMapOnMessage,
    WelcomeMessage,
)
from madvr_envy.state import EnvyState


def _base_state() -> EnvyState:
    state = EnvyState()
    state.apply(WelcomeMessage(version="1.1.3"))
    return state


def test_snapshot_from_state_is_immutable_and_comparable():
    state = _base_state()
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

    snap = snapshot_from_state(state)
    assert snap.synced is True
    assert snap.version == "1.1.3"
    assert snap.signal_present is True
    assert snap.temperatures is None
    assert snap.options == ()


def test_adapter_emits_deltas_and_events():
    adapter = EnvyStateAdapter()
    state = _base_state()

    first_snapshot, first_deltas, first_events = adapter.update(state)
    assert first_snapshot.synced is True
    assert first_deltas == []
    assert first_events == []

    state.apply(KeyPressMessage(button="MENU"))
    state.apply(ChangeOptionMessage(option_type="INTEGER", option_id_path="hdrNits", current_value=120, effective_value=121))
    state.apply(ResetTemporaryMessage())
    state.apply(DisplayChangedMessage())
    state.apply(ToneMapOnMessage())
    state.apply(StoreSettingsMessage(target="Installer", storage_name="Installer Settings"))

    _, deltas, events = adapter.update(state)
    changed_fields = {delta.field for delta in deltas}
    event_kinds = [event.kind for event in events]

    assert "last_button_event" in changed_fields
    assert "options" in changed_fields
    assert "temporary_reset_count" in changed_fields
    assert "display_changed_count" in changed_fields
    assert "tone_map_enabled" in changed_fields
    assert "last_store_settings" in changed_fields

    assert "button" in event_kinds
    assert "temporary_reset" in event_kinds
    assert "display_changed" in event_kinds
    assert "settings_stored" in event_kinds
