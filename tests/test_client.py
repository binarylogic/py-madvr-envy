import asyncio
from collections import deque

import pytest

from madvr_envy.adapter import EnvyStateAdapter
from madvr_envy.client import MadvrEnvyClient
from madvr_envy.exceptions import (
    CommandRejectedError,
    ConnectionFailedError,
    EnumerationTimeoutError,
    NotConnectedError,
)


class FakeTransport:
    def __init__(self, incoming_lines=None, connect_exception=None):
        self.connected = False
        self.sent: list[str] = []
        self.connect_calls = 0
        self.close_calls = 0
        self._incoming = asyncio.Queue()
        self._connect_exception = connect_exception

        for line in incoming_lines or []:
            self._incoming.put_nowait(line)

    async def connect(self, timeout):
        self.connect_calls += 1
        if self._connect_exception is not None:
            raise self._connect_exception
        self.connected = True

    async def close(self):
        self.close_calls += 1
        self.connected = False

    async def read_line(self, timeout):
        if not self.connected:
            raise NotConnectedError()

        if timeout is None:
            item = await self._incoming.get()
        else:
            item = await asyncio.wait_for(self._incoming.get(), timeout=timeout)

        if item is None:
            self.connected = False
            raise NotConnectedError("Connection closed by peer.")

        return item

    async def send_line(self, line, timeout):
        if not self.connected:
            raise NotConnectedError()
        self.sent.append(line)

    def push(self, line):
        self._incoming.put_nowait(line)


class FakeTransportFactory:
    def __init__(self, transports):
        self._transports = deque(transports)

    def __call__(self):
        return self._transports.popleft()


@pytest.mark.asyncio
async def test_start_wait_synced_and_stop_are_idempotent():
    transport = FakeTransport(incoming_lines=["WELCOME to Envy v1.1.3"])
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.start()
    await client.wait_synced(timeout=1)

    assert transport.connect_calls == 1
    assert client.state.version == "1.1.3"

    await client.stop()
    await client.stop()
    assert transport.close_calls == 1


@pytest.mark.asyncio
async def test_command_wait_for_ack_returns_ok_message():
    transport = FakeTransport(incoming_lines=["WELCOME to Envy v1.1.3"])
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    async def push_ack():
        await asyncio.sleep(0)
        transport.push("OK")

    asyncio.create_task(push_ack())
    ack = await client.command("GetMacAddress", wait_for_ack=True, ack_timeout=0.5)

    assert ack is not None
    assert transport.sent[-1] == "GetMacAddress"

    await client.stop()


@pytest.mark.asyncio
async def test_typed_command_wrapper_sends_expected_payload():
    transport = FakeTransport(incoming_lines=["WELCOME to Envy v1.1.3"])
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    await client.display_message(3, "Hello world", wait_for_ack=False)
    await client.change_option("temporary\\hdrNits", 121, wait_for_ack=False)
    await client.toggle_option("ToneMap", wait_for_ack=False)
    await client.tone_map_on(wait_for_ack=False)
    await client.tone_map_off(wait_for_ack=False)

    assert transport.sent[-5] == 'DisplayMessage 3 "Hello world"'
    assert transport.sent[-4] == "ChangeOption temporary\\hdrNits 121"
    assert transport.sent[-3] == "Toggle ToneMap"
    assert transport.sent[-2] == "ToneMapOn"
    assert transport.sent[-1] == "ToneMapOff"

    await client.stop()


@pytest.mark.asyncio
async def test_command_wait_for_ack_raises_on_error_message():
    transport = FakeTransport(incoming_lines=["WELCOME to Envy v1.1.3"])
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    async def push_error():
        await asyncio.sleep(0)
        transport.push('ERROR "invalid command"')

    asyncio.create_task(push_error())

    with pytest.raises(CommandRejectedError):
        await client.command("Nope", wait_for_ack=True, ack_timeout=0.5)

    await client.stop()


@pytest.mark.asyncio
async def test_reconnect_uses_backoff_until_success():
    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)

    first = FakeTransport(incoming_lines=["WELCOME to Envy v1.1.3", None])
    failing = FakeTransport(connect_exception=ConnectionFailedError("network down"))
    second = FakeTransport(incoming_lines=["WELCOME to Envy v1.1.4"])

    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([first, failing, second]),
        read_timeout=0.01,
        reconnect_initial_backoff=0.1,
        reconnect_max_backoff=0.4,
        reconnect_jitter=0.0,
        sleep_func=fake_sleep,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    await asyncio.wait_for(_wait_for(lambda: client.state.version == "1.1.4"), timeout=1)

    assert sleep_calls == [0.1]

    await client.stop()


@pytest.mark.asyncio
async def test_enum_profile_groups_collect_returns_items_until_end_marker():
    transport = FakeTransport(incoming_lines=["WELCOME to Envy v1.1.3"])
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    async def push_enumeration():
        await asyncio.sleep(0)
        transport.push("OK")
        transport.push('ProfileGroup displayProfiles "Displays"')
        transport.push('ProfileGroup customProfileGroup1 "Ambient Light"')
        transport.push("ProfileGroup.")

    asyncio.create_task(push_enumeration())
    groups = await client.enum_profile_groups_collect(timeout=0.5)

    assert [group.group_id for group in groups] == ["displayProfiles", "customProfileGroup1"]
    assert [group.name for group in groups] == ["Displays", "Ambient Light"]

    await client.stop()


@pytest.mark.asyncio
async def test_enum_options_collect_returns_typed_values():
    transport = FakeTransport(incoming_lines=["WELCOME to Envy v1.1.3"])
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    async def push_enumeration():
        await asyncio.sleep(0)
        transport.push("OK")
        transport.push("Option INTEGER hdrNits 120 121")
        transport.push('Option STRING hdrMode "toneMapMath" "toneMapMath"')
        transport.push("Option.")

    asyncio.create_task(push_enumeration())
    options = await client.enum_options_collect("hdrSettings", timeout=0.5)

    assert len(options) == 2
    assert options[0].option_id == "hdrNits"
    assert options[0].current_value == 120
    assert options[1].option_id == "hdrMode"
    assert options[1].current_value == "toneMapMath"

    await client.stop()


@pytest.mark.asyncio
async def test_enum_collect_timeout_raises_enumeration_timeout_error():
    transport = FakeTransport(incoming_lines=["WELCOME to Envy v1.1.3"])
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    async def push_incomplete_enumeration():
        await asyncio.sleep(0)
        transport.push("OK")
        transport.push('ProfileGroup displayProfiles "Displays"')
        # Missing "ProfileGroup." end marker on purpose

    asyncio.create_task(push_incomplete_enumeration())

    with pytest.raises(EnumerationTimeoutError) as err:
        await client.enum_profile_groups_collect(timeout=0.05)

    assert err.value.command == "EnumProfileGroups"
    assert err.value.item_type == "ProfileGroupMessage"
    assert err.value.end_type == "ProfileGroupEndMessage"
    assert err.value.items_collected == 1

    await client.stop()


@pytest.mark.asyncio
async def test_register_adapter_callback_emits_initial_and_change_events():
    transport = FakeTransport(incoming_lines=["WELCOME to Envy v1.1.3"])
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    adapter = EnvyStateAdapter()
    emissions: list[tuple[object, list[object], list[object]]] = []
    emission_event = asyncio.Event()

    def on_adapter(snapshot, deltas, events):
        emissions.append((snapshot, deltas, events))
        emission_event.set()

    handle = client.register_adapter_callback(adapter, on_adapter)

    await client.start()
    await asyncio.wait_for(emission_event.wait(), timeout=1)

    # First adapter emission should be initial snapshot
    first_snapshot, _, first_events = emissions[0]
    assert first_snapshot.synced is True
    assert any(event.kind == "initial" for event in first_events)

    emission_event.clear()
    transport.push("KeyPress MENU")
    await asyncio.wait_for(emission_event.wait(), timeout=1)

    second_snapshot, second_deltas, second_events = emissions[-1]
    assert second_snapshot.last_button_event == ("press", "MENU")
    assert any(delta.field == "last_button_event" for delta in second_deltas)
    assert any(event.kind == "button" for event in second_events)

    client.deregister_adapter_callback(handle)
    emission_count = len(emissions)
    transport.push("KeyPress UP")
    await asyncio.sleep(0.05)
    assert len(emissions) == emission_count

    await client.stop()


async def _wait_for(predicate):
    for _ in range(1000):
        if predicate():
            return
        await asyncio.sleep(0)
    raise TimeoutError("Condition not met")
