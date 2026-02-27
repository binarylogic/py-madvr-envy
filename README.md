# madVR Envy Python Library

Spec-first async Python client for madVR Envy IP Control.

This project intentionally does not inherit implementation patterns from existing community libraries. It is being built from the official Envy IP Control specification and protocol captures.

## Current API Shape

- Typed command helpers in `madvr_envy.commands`
- High-level async client in `madvr_envy.client.MadvrEnvyClient`
- Typed protocol parser in `madvr_envy.protocol`

Example:

```python
import asyncio

from madvr_envy.client import MadvrEnvyClient


async def main() -> None:
    client = MadvrEnvyClient(host="192.168.1.100")
    await client.start()
    await client.wait_synced(timeout=10)

    await client.get_mac_address(wait_for_ack=True)
    await client.display_message(3, "Hello from py-madvr-envy")
    await client.change_option("temporary\\hdrNits", 120)

    groups = await client.enum_profile_groups_collect()
    for group in groups:
        print(group.group_id, group.name)

    await client.stop()


asyncio.run(main())
```

## Protocol Basis

- Source: `https://madvrenvy.com/wp-content/uploads/EnvyIpControl.pdf`
- Document title: `madVR Envy IP Control revision 1.1.3`
- Retrieved: 2026-02-27
- HTTP metadata observed during retrieval: `Last-Modified: Mon, 20 May 2024 02:40:13 GMT`

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run ty check madvr_envy
uv run pytest -v
```

## Protocol Coverage

See [docs/PROTOCOL_COVERAGE.md](docs/PROTOCOL_COVERAGE.md) for implemented command and notification coverage.

## Enumeration Collectors

For stream enumerations, use typed collectors:

- `enum_profile_groups_collect()`
- `enum_profiles_collect(profile_group)`
- `enum_setting_pages_collect()`
- `enum_config_pages_collect()`
- `enum_options_collect(page_or_path)`

These helpers wait for protocol end markers and raise `EnumerationTimeoutError` if an end marker is not observed in time.

## HA Adapter

Use `madvr_envy.adapter.EnvyStateAdapter` to convert mutable runtime state into immutable snapshots plus typed deltas/events:

- `snapshot`: stable full-state view for coordinator data
- `deltas`: field-level changes since previous snapshot
- `events`: integration-friendly event stream (temporary resets, display changes, settings store/restore, etc.)

You can wire this directly through the client:

```python
from madvr_envy.adapter import EnvyStateAdapter

adapter = EnvyStateAdapter()

def on_update(snapshot, deltas, events):
    ...

handle = client.register_adapter_callback(adapter, on_update)
# later: client.deregister_adapter_callback(handle)
```

For Home Assistant coordinator/event-bus integration, use `madvr_envy.ha_bridge`:

- `coordinator_payload(snapshot)`
- `to_ha_events(events)`
- `build_bridge_update(snapshot, deltas, events)`

Reference coordinator wiring: `docs/ha_coordinator_example.py`.
