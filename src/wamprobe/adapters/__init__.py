"""Built-in model adapters and diagnostic baselines."""

from wamprobe.adapters.baselines import (
    ActionAgnosticAdapter,
    CopyLastFrameAdapter,
    OraclePointMassAdapter,
    WrongDirectionAdapter,
)
from wamprobe.adapters.starwam import StarWAMAdapter, StarWAMBackendResult, StarWAMRelease

__all__ = [
    "ActionAgnosticAdapter",
    "CopyLastFrameAdapter",
    "OraclePointMassAdapter",
    "StarWAMAdapter",
    "StarWAMBackendResult",
    "StarWAMRelease",
    "WrongDirectionAdapter",
]
