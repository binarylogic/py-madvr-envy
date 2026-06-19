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
    VideoState,
)
from madvr_envy.runtime_manager import EnvyRuntime, RefreshPolicy

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
    "VideoState",
    "EnvyRuntime",
    "RefreshPolicy",
    "commands",
    "adapter",
    "runtime",
]

__version__ = "2.1.0"
