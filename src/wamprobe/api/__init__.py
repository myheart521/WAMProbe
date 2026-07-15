"""Public, model-agnostic WAMProbe API."""

from wamprobe.api.capabilities import FutureRepresentation, ModelCapabilities
from wamprobe.api.counterfactual import (
    ActionBranch,
    CounterfactualValidation,
    RGBFrameReference,
    RobotAction,
    RobotFuture,
    RobotInterventionGroup,
    RobotStateFrame,
    SimulatorSnapshotDescriptor,
)
from wamprobe.api.manipulation import (
    ManipulationAction,
    ManipulationAdapter,
    ManipulationBenchmark,
    ManipulationContext,
    ManipulationInterventionGroup,
    ManipulationInterventionSuite,
    ManipulationState,
    ManipulationTrajectory,
)
from wamprobe.api.model import ActionPredictorAdapter, WAMAdapter
from wamprobe.api.robotics import ActionPrediction, InferenceRuntime, RGBFrame, RobotObservation
from wamprobe.api.types import (
    Action2D,
    Context2D,
    InterventionGroup,
    InterventionSuite,
    Trajectory2D,
    Vec2,
)

__all__ = [
    "Action2D",
    "ActionBranch",
    "ActionPrediction",
    "ActionPredictorAdapter",
    "Context2D",
    "CounterfactualValidation",
    "FutureRepresentation",
    "InterventionGroup",
    "InterventionSuite",
    "InferenceRuntime",
    "ModelCapabilities",
    "ManipulationAction",
    "ManipulationAdapter",
    "ManipulationBenchmark",
    "ManipulationContext",
    "ManipulationInterventionGroup",
    "ManipulationInterventionSuite",
    "ManipulationState",
    "ManipulationTrajectory",
    "RGBFrame",
    "RGBFrameReference",
    "RobotAction",
    "RobotFuture",
    "RobotInterventionGroup",
    "RobotObservation",
    "RobotStateFrame",
    "SimulatorSnapshotDescriptor",
    "Trajectory2D",
    "Vec2",
    "WAMAdapter",
]
