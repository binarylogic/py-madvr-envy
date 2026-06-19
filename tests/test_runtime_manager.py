import asyncio

import pytest
from test_client import FakeTransport, FakeTransportFactory, _wait_for

from madvr_envy.client import MadvrEnvyClient
from madvr_envy.runtime_manager import EnvyRuntime, RefreshPolicy


@pytest.mark.asyncio
async def test_runtime_publishes_trusted_video_after_volatile_refresh():
    now = 100.0
    transport = FakeTransport(
        incoming_lines=["WELCOME to Envy v1.1.3"],
        responses={
            "GetTemperatures": ["Temperatures 74 67 41 45", "OK"],
            "GetIncomingSignalInfo": [
                "IncomingSignalInfo 3840x2160 23.976p 2D 422 10bit HDR10 2020 TV 16:9",
                "OK",
            ],
            "GetOutgoingSignalInfo": [
                "OutgoingSignalInfo 3840x2160 23.976p 2D RGB 12bit SDR 2020 TV",
                "OK",
            ],
            "GetAspectRatio": ['AspectRatio 3840:1600 2.400 240 "Panavision"', "OK"],
            "GetMaskingRatio": ["MaskingRatio 3840:1700 2.259 220", "OK"],
            "EnumProfileGroups": ["ProfileGroup.", "OK"],
        },
    )
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
        command_timeout=0.5,
    )
    runtime = EnvyRuntime(
        client,
        policy=RefreshPolicy(volatile_video_interval=60, stale_after=15),
        clock=lambda: now,
    )
    snapshots = []
    runtime.subscribe(snapshots.append)

    await runtime.start()

    assert runtime.snapshot.video.trusted is True
    assert runtime.snapshot.video.updated_at == now
    assert snapshots[-1].video.masking_ratio is not None

    await runtime.stop()


@pytest.mark.asyncio
async def test_runtime_marks_video_untrusted_after_stale_window():
    now = 100.0
    transport = FakeTransport(
        incoming_lines=["WELCOME to Envy v1.1.3"],
        responses={
            "GetTemperatures": ["Temperatures 74 67 41 45", "OK"],
            "GetIncomingSignalInfo": [
                "IncomingSignalInfo 3840x2160 23.976p 2D 422 10bit HDR10 2020 TV 16:9",
                "OK",
            ],
            "GetOutgoingSignalInfo": [
                "OutgoingSignalInfo 3840x2160 23.976p 2D RGB 12bit SDR 2020 TV",
                "OK",
            ],
            "GetAspectRatio": ['AspectRatio 3840:1600 2.400 240 "Panavision"', "OK"],
            "GetMaskingRatio": ["MaskingRatio 3840:1700 2.259 220", "OK"],
            "EnumProfileGroups": ["ProfileGroup.", "OK"],
        },
    )
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
        command_timeout=0.5,
    )
    runtime = EnvyRuntime(
        client,
        policy=RefreshPolicy(volatile_video_interval=60, stale_after=15),
        clock=lambda: now,
    )
    snapshot_event = asyncio.Event()
    runtime.subscribe(lambda snapshot: snapshot_event.set())

    await runtime.start()
    assert runtime.snapshot.video.trusted is True

    now = 116.0
    snapshot_event.clear()
    transport.push("KeyPress MENU")
    await asyncio.wait_for(snapshot_event.wait(), timeout=1)

    assert runtime.snapshot.video.trusted is False
    assert runtime.snapshot.video.aspect_ratio is not None

    await runtime.stop()


@pytest.mark.asyncio
async def test_runtime_debounces_display_changed_geometry_refresh():
    transport = FakeTransport(
        incoming_lines=["WELCOME to Envy v1.1.3"],
        responses={
            "GetTemperatures": ["Temperatures 74 67 41 45", "OK"],
            "GetIncomingSignalInfo": [
                "IncomingSignalInfo 3840x2160 23.976p 2D 422 10bit HDR10 2020 TV 16:9",
                "OK",
            ],
            "GetOutgoingSignalInfo": [
                "OutgoingSignalInfo 3840x2160 23.976p 2D RGB 12bit SDR 2020 TV",
                "OK",
            ],
            "GetAspectRatio": ['AspectRatio 3840:1600 2.400 240 "Panavision"', "OK"],
            "GetMaskingRatio": ["MaskingRatio 3840:1700 2.259 220", "OK"],
            "EnumProfileGroups": ["ProfileGroup.", "OK"],
        },
    )
    client = MadvrEnvyClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
        command_timeout=0.5,
    )
    runtime = EnvyRuntime(
        client,
        policy=RefreshPolicy(volatile_video_interval=60, geometry_debounce=0, stale_after=15),
    )

    await runtime.start()
    transport.sent.clear()
    transport.push("DisplayChanged")

    await asyncio.wait_for(_wait_for(lambda: transport.sent == ["GetAspectRatio", "GetMaskingRatio"]), timeout=1)

    await runtime.stop()
