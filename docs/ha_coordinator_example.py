"""Reference wiring for a Home Assistant DataUpdateCoordinator integration.

This file is intentionally dependency-light and does not import Home Assistant modules,
so it can serve as a readable integration template.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from madvr_envy.adapter import EnvyStateAdapter
from madvr_envy.client import MadvrEnvyClient
from madvr_envy.ha_bridge import HABridgeDispatcher


@dataclass
class FakeCoordinator:
    """Small stand-in for Home Assistant's DataUpdateCoordinator."""

    data: dict[str, Any]

    def async_set_updated_data(self, data: dict[str, Any]) -> None:
        self.data = data


class FakeBus:
    """Small stand-in for Home Assistant event bus."""

    def async_fire(self, event_type: str, event_data: dict[str, object]) -> None:
        print(f"EVENT {event_type}: {event_data}")


async def setup_envy_runtime(host: str) -> tuple[MadvrEnvyClient, FakeCoordinator, Any]:
    """Create and wire client + adapter + bridge dispatcher."""
    client = MadvrEnvyClient(host=host)
    adapter = EnvyStateAdapter()
    coordinator = FakeCoordinator(data={})
    bus = FakeBus()
    dispatcher = HABridgeDispatcher(event_emitter=bus.async_fire)

    def on_adapter_update(snapshot, deltas, events) -> None:
        update = dispatcher.handle_adapter_update(snapshot, deltas, events)
        coordinator.async_set_updated_data(update.coordinator_data)

    handle = client.register_adapter_callback(adapter, on_adapter_update)

    await client.start()
    await client.wait_synced(timeout=10)
    return client, coordinator, handle
