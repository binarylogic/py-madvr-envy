"""High-level Envy client optimized for long-running integrations."""

from __future__ import annotations

import asyncio
import logging
import random
from collections import deque
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Protocol, TypeVar

from madvr_envy import commands as cmd
from madvr_envy import exceptions
from madvr_envy.adapter import AdapterEvent, EnvySnapshot, EnvyStateAdapter, StateDelta
from madvr_envy.protocol import (
    ConfigPageEndMessage,
    ConfigPageMessage,
    ErrorMessage,
    Message,
    OkMessage,
    OptionEndMessage,
    OptionMessage,
    ProfileEndMessage,
    ProfileGroupEndMessage,
    ProfileGroupMessage,
    ProfileMessage,
    SettingPageEndMessage,
    SettingPageMessage,
    build_command,
    parse_message,
)
from madvr_envy.state import EnvyState
from madvr_envy.transport import TcpTransport

Callback = Callable[[str, Message | None], None]
AdapterCallback = Callable[[EnvySnapshot, list[StateDelta], list[AdapterEvent]], None]
RandomFunc = Callable[[], float]
ItemMessageT = TypeVar("ItemMessageT", bound=Message)
EndMessageT = TypeVar("EndMessageT", bound=Message)


class Transport(Protocol):
    @property
    def connected(self) -> bool: ...

    async def connect(self, timeout: float | None) -> None: ...

    async def close(self) -> None: ...

    async def read_line(self, timeout: float | None) -> str: ...

    async def send_line(self, line: str, timeout: float | None) -> None: ...


class MadvrEnvyClient:
    DEFAULT_PORT = 44077
    DEFAULT_CONNECT_TIMEOUT = 3.0
    DEFAULT_COMMAND_TIMEOUT = 2.0
    DEFAULT_READ_TIMEOUT = 30.0
    DEFAULT_RECONNECT_INITIAL_BACKOFF = 1.0
    DEFAULT_RECONNECT_MAX_BACKOFF = 30.0
    DEFAULT_RECONNECT_JITTER = 0.2

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        connect_timeout: float | None = DEFAULT_CONNECT_TIMEOUT,
        command_timeout: float | None = DEFAULT_COMMAND_TIMEOUT,
        read_timeout: float | None = DEFAULT_READ_TIMEOUT,
        reconnect_initial_backoff: float = DEFAULT_RECONNECT_INITIAL_BACKOFF,
        reconnect_max_backoff: float = DEFAULT_RECONNECT_MAX_BACKOFF,
        reconnect_jitter: float = DEFAULT_RECONNECT_JITTER,
        auto_reconnect: bool = True,
        logger: logging.Logger | None = None,
        transport_factory: Callable[[], Transport] | None = None,
        sleep_func: Callable[[float], Awaitable[None]] | None = None,
        random_func: RandomFunc | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout
        self.read_timeout = read_timeout

        self.reconnect_initial_backoff = reconnect_initial_backoff
        self.reconnect_max_backoff = reconnect_max_backoff
        self.reconnect_jitter = reconnect_jitter
        self.auto_reconnect = auto_reconnect

        self.logger = logger if logger is not None else logging.getLogger(__name__)
        self.state = EnvyState()

        self._callbacks: set[Callback] = set()
        self._listen_task: asyncio.Task[None] | None = None
        self._sync_event = asyncio.Event()
        self._stopping = False

        self._transport_factory = transport_factory or (lambda: TcpTransport(self.host, self.port))
        self._transport: Transport | None = None

        self._sleep = sleep_func or asyncio.sleep
        self._random = random_func or random.random

        self._command_lock = asyncio.Lock()
        self._ack_waiters: deque[asyncio.Future[Message]] = deque()

    @property
    def connected(self) -> bool:
        return self._transport is not None and self._transport.connected

    def register_callback(self, callback: Callback) -> None:
        self._callbacks.add(callback)

    def deregister_callback(self, callback: Callback) -> None:
        self._callbacks.discard(callback)

    def register_adapter_callback(self, adapter: EnvyStateAdapter, callback: AdapterCallback) -> Callback:
        """Register a callback that receives adapter snapshots, deltas and events."""

        def wrapped(event: str, message: Message | None) -> None:
            if event != "received_message" or message is None:
                return

            initial = adapter.last_snapshot is None
            snapshot, deltas, events = adapter.update(self.state)

            if initial:
                callback(snapshot, deltas, [AdapterEvent(kind="initial", payload={}), *events])
                return

            if not deltas and not events:
                return

            callback(snapshot, deltas, events)

        self.register_callback(wrapped)
        return wrapped

    def deregister_adapter_callback(self, callback: Callback) -> None:
        """Deregister a callback previously returned by ``register_adapter_callback``."""
        self.deregister_callback(callback)

    async def start(self) -> None:
        if self._listen_task is not None and not self._listen_task.done():
            return

        self._stopping = False
        await self._connect()
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop(self) -> None:
        self._stopping = True

        if self._listen_task is not None:
            self._listen_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listen_task
            self._listen_task = None

        await self._disconnect_statefully()

    async def wait_synced(self, timeout: float | None = 10.0) -> None:
        if timeout is None:
            await self._sync_event.wait()
            return
        await asyncio.wait_for(self._sync_event.wait(), timeout=timeout)

    async def command(
        self,
        name: str,
        *args: str | int,
        wait_for_ack: bool = False,
        ack_timeout: float | None = None,
    ) -> Message | None:
        return await self._command(
            build_command(name, *args),
            wait_for_ack=wait_for_ack,
            ack_timeout=ack_timeout,
        )

    async def send_raw(self, line: str, wait_for_ack: bool = False, ack_timeout: float | None = None) -> Message | None:
        return await self._command(line, wait_for_ack=wait_for_ack, ack_timeout=ack_timeout)

    async def heartbeat(self, wait_for_ack: bool = False) -> Message | None:
        return await self.send_raw(cmd.heartbeat(), wait_for_ack=wait_for_ack)

    async def bye(self, wait_for_ack: bool = False) -> Message | None:
        return await self.send_raw(cmd.bye(), wait_for_ack=wait_for_ack)

    async def power_off(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.power_off(), wait_for_ack=wait_for_ack)

    async def standby(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.standby(), wait_for_ack=wait_for_ack)

    async def restart(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.restart(), wait_for_ack=wait_for_ack)

    async def reload_software(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.reload_software(), wait_for_ack=wait_for_ack)

    async def open_menu(self, menu: cmd.MenuName | str, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.open_menu(menu), wait_for_ack=wait_for_ack)

    async def close_menu(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.close_menu(), wait_for_ack=wait_for_ack)

    async def key_press(self, button: cmd.RemoteButton | str, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.key_press(button), wait_for_ack=wait_for_ack)

    async def key_hold(self, button: cmd.RemoteButton | str, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.key_hold(button), wait_for_ack=wait_for_ack)

    async def display_message(self, timeout_seconds: int, text: str, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.display_message(timeout_seconds, text), wait_for_ack=wait_for_ack)

    async def get_incoming_signal_info(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.get_incoming_signal_info(), wait_for_ack=wait_for_ack)

    async def get_outgoing_signal_info(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.get_outgoing_signal_info(), wait_for_ack=wait_for_ack)

    async def get_aspect_ratio(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.get_aspect_ratio(), wait_for_ack=wait_for_ack)

    async def get_masking_ratio(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.get_masking_ratio(), wait_for_ack=wait_for_ack)

    async def get_temperatures(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.get_temperatures(), wait_for_ack=wait_for_ack)

    async def get_mac_address(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.get_mac_address(), wait_for_ack=wait_for_ack)

    async def set_aspect_ratio_mode(self, mode: cmd.AspectRatioMode | str, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.set_aspect_ratio_mode(mode), wait_for_ack=wait_for_ack)

    async def activate_profile(self, profile_group: str | int, profile_id: int, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.activate_profile(profile_group, profile_id), wait_for_ack=wait_for_ack)

    async def get_active_profile(self, profile_group: str | int, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.get_active_profile(profile_group), wait_for_ack=wait_for_ack)

    async def enum_profiles(self, profile_group: str | int, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.enum_profiles(profile_group), wait_for_ack=wait_for_ack)

    async def enum_profile_groups_collect(self, timeout: float = 3.0) -> list[ProfileGroupMessage]:
        return await self._collect_enumeration(
            command_line=cmd.enum_profile_groups(),
            item_type=ProfileGroupMessage,
            end_type=ProfileGroupEndMessage,
            timeout=timeout,
        )

    async def enum_profiles_collect(self, profile_group: str | int, timeout: float = 3.0) -> list[ProfileMessage]:
        return await self._collect_enumeration(
            command_line=cmd.enum_profiles(profile_group),
            item_type=ProfileMessage,
            end_type=ProfileEndMessage,
            timeout=timeout,
        )

    async def enum_profile_groups(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.enum_profile_groups(), wait_for_ack=wait_for_ack)

    async def enum_setting_pages(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.enum_setting_pages(), wait_for_ack=wait_for_ack)

    async def enum_setting_pages_collect(self, timeout: float = 3.0) -> list[SettingPageMessage]:
        return await self._collect_enumeration(
            command_line=cmd.enum_setting_pages(),
            item_type=SettingPageMessage,
            end_type=SettingPageEndMessage,
            timeout=timeout,
        )

    async def enum_config_pages(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.enum_config_pages(), wait_for_ack=wait_for_ack)

    async def enum_config_pages_collect(self, timeout: float = 3.0) -> list[ConfigPageMessage]:
        return await self._collect_enumeration(
            command_line=cmd.enum_config_pages(),
            item_type=ConfigPageMessage,
            end_type=ConfigPageEndMessage,
            timeout=timeout,
        )

    async def enum_options(self, page_or_path: str, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.enum_options(page_or_path), wait_for_ack=wait_for_ack)

    async def enum_options_collect(self, page_or_path: str, timeout: float = 3.0) -> list[OptionMessage]:
        return await self._collect_enumeration(
            command_line=cmd.enum_options(page_or_path),
            item_type=OptionMessage,
            end_type=OptionEndMessage,
            timeout=timeout,
        )

    async def query_option(self, option_id_or_path: str, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.query_option(option_id_or_path), wait_for_ack=wait_for_ack)

    async def change_option(self, option_id_path: str, value: cmd.OptionValue, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.change_option(option_id_path, value), wait_for_ack=wait_for_ack)

    async def toggle_option(self, option_name: str, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.toggle_option(option_name), wait_for_ack=wait_for_ack)

    async def tone_map_on(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.tone_map_on(), wait_for_ack=wait_for_ack)

    async def tone_map_off(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.tone_map_off(), wait_for_ack=wait_for_ack)

    async def hotplug(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.hotplug(), wait_for_ack=wait_for_ack)

    async def refresh_license_info(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.refresh_license_info(), wait_for_ack=wait_for_ack)

    async def force_1080p60_output(self, wait_for_ack: bool = True) -> Message | None:
        return await self.send_raw(cmd.force_1080p60_output(), wait_for_ack=wait_for_ack)

    async def _connect(self) -> None:
        if self.connected:
            return

        self._sync_event.clear()
        self.state.reset_runtime_values()

        self._transport = self._transport_factory()
        await self._transport.connect(timeout=self.connect_timeout)
        self._emit("connected", None)

    async def _disconnect_statefully(self) -> None:
        transport = self._transport
        self._transport = None

        self._sync_event.clear()
        self.state.reset_runtime_values()

        while self._ack_waiters:
            waiter = self._ack_waiters.popleft()
            if not waiter.done():
                waiter.set_exception(exceptions.NotConnectedError())

        if transport is None:
            return

        with suppress(OSError):
            await transport.close()

        self._emit("disconnected", None)

    async def _listen_loop(self) -> None:
        try:
            while not self._stopping:
                try:
                    line = await self._read_line()
                    message = parse_message(line)

                    self.state.apply(message)
                    self._resolve_ack_waiter(message)
                    self._emit("received_message", message)

                    if self.state.synced and not self._sync_event.is_set():
                        self._sync_event.set()
                except TimeoutError:
                    continue
                except (exceptions.NotConnectedError, OSError):
                    await self._disconnect_statefully()
                    reconnected = await self._attempt_reconnect_until_success()
                    if not reconnected:
                        break
        except asyncio.CancelledError:
            pass

    async def _read_line(self) -> str:
        if self._transport is None:
            raise exceptions.NotConnectedError()
        return await self._transport.read_line(timeout=self.read_timeout)

    def _resolve_ack_waiter(self, message: Message) -> None:
        if not isinstance(message, (OkMessage, ErrorMessage)):
            return
        if not self._ack_waiters:
            return

        waiter = self._ack_waiters.popleft()
        if not waiter.done():
            waiter.set_result(message)

    async def _command(
        self,
        line: str,
        wait_for_ack: bool = False,
        ack_timeout: float | None = None,
    ) -> Message | None:
        if self._transport is None:
            raise exceptions.NotConnectedError()

        waiter: asyncio.Future[Message] | None = None

        async with self._command_lock:
            if wait_for_ack:
                loop = asyncio.get_running_loop()
                waiter = loop.create_future()
                self._ack_waiters.append(waiter)

            try:
                await self._transport.send_line(line, timeout=self.command_timeout)
            except Exception:
                if waiter is not None and waiter in self._ack_waiters:
                    self._ack_waiters.remove(waiter)
                raise

        if waiter is None:
            return None

        timeout = self.command_timeout if ack_timeout is None else ack_timeout
        try:
            ack_message = await asyncio.wait_for(waiter, timeout=timeout)
        except TimeoutError:
            if waiter in self._ack_waiters:
                self._ack_waiters.remove(waiter)
            raise

        if isinstance(ack_message, ErrorMessage):
            raise exceptions.CommandRejectedError(line, ack_message.error)

        return ack_message

    async def _attempt_reconnect_until_success(self) -> bool:
        if self._stopping or not self.auto_reconnect:
            return False

        delay = max(0.0, self.reconnect_initial_backoff)

        while not self._stopping and self.auto_reconnect:
            try:
                await self._connect()
                return True
            except (exceptions.ConnectionFailedError, exceptions.ConnectionTimeoutError):
                capped_delay = min(delay, self.reconnect_max_backoff)
                jitter_amount = capped_delay * self.reconnect_jitter * self._random()
                await self._sleep(capped_delay + jitter_amount)
                delay = min(max(capped_delay * 2, self.reconnect_initial_backoff), self.reconnect_max_backoff)

        return False

    async def _collect_enumeration(
        self,
        command_line: str,
        item_type: type[ItemMessageT],
        end_type: type[EndMessageT],
        timeout: float,
    ) -> list[ItemMessageT]:
        queue: asyncio.Queue[Message] = asyncio.Queue()
        items: list[ItemMessageT] = []

        def on_message(event: str, message: Message | None) -> None:
            if event != "received_message" or message is None:
                return
            if isinstance(message, (item_type, end_type)):
                queue.put_nowait(message)

        self.register_callback(on_message)
        try:
            await self.send_raw(command_line, wait_for_ack=True)

            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=timeout)
                except TimeoutError as err:
                    raise exceptions.EnumerationTimeoutError(
                        command=command_line,
                        item_type=item_type.__name__,
                        end_type=end_type.__name__,
                        timeout=timeout,
                        items_collected=len(items),
                    ) from err
                if isinstance(message, end_type):
                    return items
                if isinstance(message, item_type):
                    items.append(message)
        finally:
            self.deregister_callback(on_message)

    def _emit(self, event: str, message: Message | None) -> None:
        for callback in tuple(self._callbacks):
            try:
                callback(event, message)
            except Exception:
                self.logger.exception("Callback raised an exception during '%s'", event)
