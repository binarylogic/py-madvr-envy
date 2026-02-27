# Architecture

## Design goals

- Reliability over convenience
- Deterministic async lifecycle (`start`, `wait_synced`, `stop`)
- Typed protocol models and parser with explicit `UnknownMessage` fallback
- State reducer isolated from I/O and command transport
- Reconnect logic with bounded backoff and jitter

## Layers

- `transport.py`: async TCP line transport
- `protocol.py`: command builder + message parser + typed models
- `commands.py`: typed command constructors aligned with spec operations
- `state.py`: canonical state model and reducer
- `client.py`: lifecycle orchestration, reconnect, callbacks, command ACK handling
  plus typed enumeration collectors (`enum_*_collect`) that consume stream items until protocol end markers.
  Enumeration collectors raise `EnumerationTimeoutError` with command/type context when end markers are not observed in time.
- `adapter.py`: immutable snapshot + delta/event adapter layer for Home Assistant coordinators.
- `ha_bridge.py`: transforms adapter output into coordinator payloads + HA event bus messages.
  Includes `HABridgeDispatcher` for runtime callback wiring.

## What we explicitly avoid

- Ad-hoc dict mutation across multiple tasks
- Swallowing protocol parse errors
- Unbounded background task growth
- Implicit command formatting and silent coercion
