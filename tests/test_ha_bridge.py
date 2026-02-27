from madvr_envy.adapter import AdapterEvent, StateDelta, snapshot_from_state
from madvr_envy.ha_bridge import HABridgeDispatcher, build_bridge_update, coordinator_payload, to_ha_events
from madvr_envy.protocol import (
    AspectRatioMessage,
    ChangeOptionMessage,
    IncomingSignalInfoMessage,
    KeyPressMessage,
    MaskingRatioMessage,
    OutgoingSignalInfoMessage,
    ToneMapOnMessage,
    WelcomeMessage,
)
from madvr_envy.state import EnvyState


def _state_for_bridge() -> EnvyState:
    state = EnvyState()
    state.apply(WelcomeMessage(version="1.1.3"))
    state.apply(ToneMapOnMessage())
    state.apply(KeyPressMessage(button="MENU"))
    state.apply(ChangeOptionMessage(option_type="INTEGER", option_id_path="hdrNits", current_value=120, effective_value=121))
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
    state.apply(
        OutgoingSignalInfoMessage(
            resolution="3840x2160",
            frame_rate="23.976p",
            signal_type="2D",
            color_space="RGB",
            bit_depth="12bit",
            hdr_mode="SDR",
            colorimetry="2020",
            black_levels="TV",
        )
    )
    state.apply(
        AspectRatioMessage(
            resolution="3840:1600",
            decimal_ratio=2.4,
            integer_ratio=240,
            name="Panavision",
        )
    )
    state.apply(
        MaskingRatioMessage(
            resolution="3840:1700",
            decimal_ratio=2.259,
            integer_ratio=220,
        )
    )
    return state


def test_coordinator_payload_contains_normalized_fields():
    snapshot = snapshot_from_state(_state_for_bridge())
    payload = coordinator_payload(snapshot)

    assert payload["available"] is True
    assert payload["power_state"] == "on"
    assert payload["version"] == "1.1.3"
    assert payload["tone_map_enabled"] is True
    assert payload["incoming_signal"]["aspect_ratio"] == "16:9"
    assert payload["outgoing_signal"]["hdr_mode"] == "SDR"
    assert payload["aspect_ratio"]["name"] == "Panavision"
    assert payload["masking_ratio"]["decimal_ratio"] == 2.259
    assert payload["last_button_event"] == ("press", "MENU")
    assert payload["options"]["hdrNits"]["type"] == "INTEGER"
    assert payload["options"]["hdrNits"]["current"] == 120
    assert payload["options"]["hdrNits"]["effective"] == 121


def test_to_ha_events_maps_kinds_and_payloads():
    events = [
        AdapterEvent(kind="temporary_reset", payload={"count": 2, "increment": 1}),
        AdapterEvent(kind="button", payload={"button": ("press", "UP")}),
    ]
    mapped = to_ha_events(events)

    assert mapped[0].event_type == "madvr_envy.temporary_reset"
    assert mapped[0].event_data["count"] == 2
    assert mapped[1].event_type == "madvr_envy.button"
    assert mapped[1].event_data["button"] == ("press", "UP")


def test_build_bridge_update_collects_changed_fields_and_events():
    snapshot = snapshot_from_state(_state_for_bridge())
    deltas = [
        StateDelta(field="tone_map_enabled", old=None, new=True),
        StateDelta(field="last_button_event", old=None, new=("press", "MENU")),
    ]
    events = [AdapterEvent(kind="button", payload={"button": ("press", "MENU")})]

    update = build_bridge_update(snapshot, deltas, events)

    assert update.coordinator_data["tone_map_enabled"] is True
    assert update.changed_fields == ("tone_map_enabled", "last_button_event")
    assert len(update.bus_events) == 1
    assert update.bus_events[0].event_type == "madvr_envy.button"


def test_dispatcher_handles_update_and_emits_events():
    snapshot = snapshot_from_state(_state_for_bridge())
    deltas = [StateDelta(field="last_button_event", old=None, new=("press", "MENU"))]
    events = [AdapterEvent(kind="button", payload={"button": ("press", "MENU")})]

    emitted: list[tuple[str, dict[str, object]]] = []

    def emitter(event_type: str, event_data: dict[str, object]) -> None:
        emitted.append((event_type, event_data))

    dispatcher = HABridgeDispatcher(event_emitter=emitter)
    update = dispatcher.handle_adapter_update(snapshot, deltas, events)

    assert dispatcher.last_update is not None
    assert update.changed_fields == ("last_button_event",)
    assert emitted == [("madvr_envy.button", {"button": ("press", "MENU")})]
