"""madVR Envy async client library."""

from madvr_envy import adapter, commands, runtime
from madvr_envy.client import MadvrEnvyClient
from madvr_envy.runtime import (
    ActiveProfile,
    AspectRatio,
    EnvyDeviceSnapshot,
    MaskingRatio,
    PowerState,
    Profile,
    ProfileCatalog,
    ProfileGroup,
    SignalInfo,
    Temperatures,
)

__all__ = [
    "MadvrEnvyClient",
    "ActiveProfile",
    "AspectRatio",
    "EnvyDeviceSnapshot",
    "MaskingRatio",
    "PowerState",
    "Profile",
    "ProfileCatalog",
    "ProfileGroup",
    "SignalInfo",
    "Temperatures",
    "commands",
    "adapter",
    "runtime",
]

__version__ = "2.0.0"
