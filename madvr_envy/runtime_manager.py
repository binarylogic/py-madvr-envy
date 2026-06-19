"""Runtime freshness policy for long-running madVR Envy integrations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, replace
from typing import Any

from madvr_envy import exceptions
from madvr_envy.client import MadvrEnvyClient
from madvr_envy.protocol import (
    AspectRatioMessage,
    DisplayChangedMessage,
    IncomingSignalInfoMessage,
    MaskingRatioMessage,
    Message,
    NoSignalMessage,
    OutgoingSignalInfoMessage,
)
from madvr_envy.runtime import EnvyDeviceSnapshot, PowerState, VideoState

SnapshotCallback = Callable[[EnvyDeviceSnapshot], None]
Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class RefreshPolicy:
    """Refresh cadence and freshness thresholds for volatile Envy state."""

    volatile_video_interval: float = 5.0
    geometry_debounce: float = 0.75
    stale_after: float = 15.0
    sync_timeout: float | None = 10.0


class EnvyRuntime:
    """Own Envy connection lifecycle, volatile refreshes, and trusted snapshots."""

    def __init__(
        self,
        client: MadvrEnvyClient,
        *,
        policy: RefreshPolicy | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.client = client
        self.policy = policy or RefreshPolicy()
        self._clock = clock
        self._callbacks: set[SnapshotCallback] = set()
        self._client_callback_registered = False
        self._started = False
        self._volatile_task: asyncio.Task[None] | None = None
        self._geometry_task: asyncio.Task[None] | None = None
        self._video_updated_at: float | None = None
        self._snapshot = self._trusted_snapshot(self.client.device_snapshot)

    @property
    def snapshot(self) -> EnvyDeviceSnapshot:
        """Return the last published freshness-qualified snapshot."""
        return self._snapshot

    def subscribe(self, callback: SnapshotCallback) -> Callable[[], None]:
        """Subscribe to snapshots and return an unsubscribe callback."""
        self._callbacks.add(callback)

        def unsubscribe() -> None:
            self._callbacks.discard(callback)

        return unsubscribe

    async def start(self) -> None:
        """Start the protocol client and volatile refresh policy."""
        if self._started:
            return
        self.client.auto_reconnect = True
        if not self._client_callback_registered:
            self.client.register_callback(self._handle_client_event)
            self._client_callback_registered = True
        try:
            await self.client.start()
            await self.client.wait_synced(timeout=self.policy.sync_timeout)
            try:
                await self.refresh_bootstrap()
            except (TimeoutError, exceptions.MadvrEnvyError, OSError):
                self._publish(self.client.device_snapshot)
        except Exception:
            self._started = False
            raise
        self._started = True
        self._start_volatile_task()

    async def stop(self) -> None:
        """Stop refresh tasks and the underlying protocol client."""
        self._started = False
        for task in (self._volatile_task, self._geometry_task):
            if task is not None:
                task.cancel()
        for task in (self._volatile_task, self._geometry_task):
            if task is not None:
                with suppress(asyncio.CancelledError):
                    await task
        self._volatile_task = None
        self._geometry_task = None
        if self._client_callback_registered:
            self.client.deregister_callback(self._handle_client_event)
            self._client_callback_registered = False
        with suppress(
            RuntimeError,
            TimeoutError,
            exceptions.MadvrEnvyError,
            OSError,
        ):
            await self.client.stop()
        self._publish(self.client.device_snapshot)

    async def refresh_bootstrap(self) -> EnvyDeviceSnapshot:
        """Refresh complete bootstrap state and publish a trusted snapshot."""
        snapshot = await self.client.refresh_device()
        if snapshot.signal_present is True:
            self._video_updated_at = self._now()
        self._publish(snapshot)
        return self._snapshot

    async def refresh_volatile_video(self) -> EnvyDeviceSnapshot:
        """Refresh signal and geometry state without touching static catalogs."""
        snapshot = await self.client.refresh_volatile_video()
        if snapshot.signal_present is True:
            self._video_updated_at = self._now()
        elif snapshot.signal_present is False:
            self._video_updated_at = None
        self._publish(snapshot)
        return self._snapshot

    async def refresh_geometry(self) -> EnvyDeviceSnapshot:
        """Refresh aspect and masking geometry when signal is known present."""
        if self.client.device_snapshot.signal_present is not True:
            self._publish(self.client.device_snapshot)
            return self._snapshot
        snapshot = await self.client.refresh_video_geometry()
        self._video_updated_at = self._now()
        self._publish(snapshot)
        return self._snapshot

    def _handle_client_event(self, event: str, message: Message | None = None) -> None:
        if not self._started:
            return
        if event == "received_message":
            if isinstance(message, NoSignalMessage):
                self._video_updated_at = None
            elif (
                isinstance(
                    message,
                    (
                        AspectRatioMessage,
                        IncomingSignalInfoMessage,
                        MaskingRatioMessage,
                        OutgoingSignalInfoMessage,
                    ),
                )
                and self.client.device_snapshot.signal_present is True
                and (
                    self.client.device_snapshot.aspect_ratio is not None
                    and self.client.device_snapshot.masking_ratio is not None
                )
            ):
                self._video_updated_at = self._now()
            self._publish(self.client.device_snapshot)
            if isinstance(message, DisplayChangedMessage):
                self._schedule_geometry_refresh()
            return

        if event in {"connected", "disconnected"}:
            if event == "disconnected":
                self._video_updated_at = None
                self._publish(replace(self.client.device_snapshot, connected=False, synced=False))
                return
            self._publish(self.client.device_snapshot)

    def _start_volatile_task(self) -> None:
        if self._volatile_task is not None and not self._volatile_task.done():
            return
        self._volatile_task = asyncio.create_task(self._run_volatile_loop())

    async def _run_volatile_loop(self) -> None:
        try:
            while self._started:
                await asyncio.sleep(self.policy.volatile_video_interval)
                snapshot = self.client.device_snapshot
                if not snapshot.can_send_live_commands or snapshot.power_state is not PowerState.ON:
                    continue
                try:
                    await self.refresh_volatile_video()
                except (TimeoutError, exceptions.MadvrEnvyError, OSError):
                    self._publish(self.client.device_snapshot)
        except asyncio.CancelledError:
            raise

    def _schedule_geometry_refresh(self) -> None:
        if self._geometry_task is not None and not self._geometry_task.done():
            self._geometry_task.cancel()
        self._geometry_task = asyncio.create_task(self._refresh_geometry_after_debounce())

    async def _refresh_geometry_after_debounce(self) -> None:
        try:
            await asyncio.sleep(self.policy.geometry_debounce)
            if not self.client.device_snapshot.can_send_live_commands:
                return
            await self.refresh_geometry()
        except asyncio.CancelledError:
            raise
        except (TimeoutError, exceptions.MadvrEnvyError, OSError):
            self._publish(self.client.device_snapshot)

    def _publish(self, snapshot: EnvyDeviceSnapshot) -> None:
        self._snapshot = self._trusted_snapshot(snapshot)
        for callback in tuple(self._callbacks):
            callback(self._snapshot)

    def _trusted_snapshot(self, snapshot: EnvyDeviceSnapshot) -> EnvyDeviceSnapshot:
        video = VideoState(
            signal_present=snapshot.signal_present,
            aspect_ratio=snapshot.aspect_ratio,
            masking_ratio=snapshot.masking_ratio,
            updated_at=self._video_updated_at,
            trusted=self._video_trusted(snapshot),
        )
        return replace(snapshot, video=video)

    def _video_trusted(self, snapshot: EnvyDeviceSnapshot) -> bool:
        if snapshot.signal_present is not True:
            return False
        if snapshot.aspect_ratio is None or snapshot.masking_ratio is None:
            return False
        if self._video_updated_at is None:
            return False
        return self._now() - self._video_updated_at <= self.policy.stale_after

    def _now(self) -> float:
        if self._clock is not None:
            return self._clock()
        try:
            return asyncio.get_running_loop().time()
        except RuntimeError:
            return 0.0


def snapshot_to_dict(snapshot: EnvyDeviceSnapshot) -> dict[str, Any]:
    """Return a small integration-friendly snapshot summary."""
    return {
        "power_state": snapshot.power_state.value,
        "connected": snapshot.connected,
        "synced": snapshot.synced,
        "signal_present": snapshot.signal_present,
        "video_trusted": snapshot.video.trusted,
        "video_updated_at": snapshot.video.updated_at,
        "aspect_ratio": snapshot.video.aspect_ratio.decimal_ratio if snapshot.video.aspect_ratio else None,
        "masking_ratio": snapshot.video.masking_ratio.decimal_ratio if snapshot.video.masking_ratio else None,
    }
