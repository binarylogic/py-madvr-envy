"""Library exception types."""

from __future__ import annotations


class MadvrEnvyError(Exception):
    """Base exception for madvr_envy."""


class ConnectionFailedError(MadvrEnvyError):
    """TCP connection could not be established."""


class ConnectionTimeoutError(MadvrEnvyError):
    """TCP connection timed out."""


class NotConnectedError(MadvrEnvyError):
    """Operation requires an active connection."""


class CommandRejectedError(MadvrEnvyError):
    """Command was rejected by Envy."""

    def __init__(self, command: str, error: str) -> None:
        super().__init__(f"Command '{command}' rejected: {error}")
        self.command = command
        self.error = error


class EnumerationTimeoutError(MadvrEnvyError):
    """Enumeration did not produce an end marker in time."""

    def __init__(
        self,
        command: str,
        item_type: str,
        end_type: str,
        timeout: float,
        items_collected: int,
    ) -> None:
        super().__init__(
            f"Enumeration timed out for '{command}' after {timeout}s "
            f"(item={item_type}, end={end_type}, collected={items_collected})"
        )
        self.command = command
        self.item_type = item_type
        self.end_type = end_type
        self.timeout = timeout
        self.items_collected = items_collected
