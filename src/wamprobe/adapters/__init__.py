"""Built-in model adapters and diagnostic baselines."""

from wamprobe.adapters.baselines import (
    ActionAgnosticAdapter,
    CopyLastFrameAdapter,
    OraclePointMassAdapter,
    WrongDirectionAdapter,
)

__all__ = [
    "ActionAgnosticAdapter",
    "CopyLastFrameAdapter",
    "OraclePointMassAdapter",
    "WrongDirectionAdapter",
]
