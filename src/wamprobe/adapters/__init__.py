"""Built-in model adapters and diagnostic baselines."""

from wamprobe.adapters.baselines import (
    ActionAgnosticAdapter,
    CopyLastFrameAdapter,
    NoisyLinearAdapter,
    OraclePointMassAdapter,
    WrongDirectionAdapter,
)
from wamprobe.adapters.manipulation import (
    ActionAgnosticManipulationAdapter,
    CopyLastManipulationAdapter,
    NoisyManipulationAdapter,
    OracleManipulationAdapter,
    WrongDirectionManipulationAdapter,
)
from wamprobe.adapters.starwam import StarWAMAdapter, StarWAMBackendResult, StarWAMRelease

__all__ = [
    "ActionAgnosticAdapter",
    "CopyLastFrameAdapter",
    "CopyLastManipulationAdapter",
    "ActionAgnosticManipulationAdapter",
    "NoisyManipulationAdapter",
    "NoisyLinearAdapter",
    "OraclePointMassAdapter",
    "OracleManipulationAdapter",
    "StarWAMAdapter",
    "StarWAMBackendResult",
    "StarWAMRelease",
    "WrongDirectionAdapter",
    "WrongDirectionManipulationAdapter",
]
