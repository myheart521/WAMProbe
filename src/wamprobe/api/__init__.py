"""Public, model-agnostic WAMProbe API."""

from wamprobe.api.capabilities import FutureRepresentation, ModelCapabilities
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
    "ActionPrediction",
    "ActionPredictorAdapter",
    "Context2D",
    "FutureRepresentation",
    "InterventionGroup",
    "InterventionSuite",
    "InferenceRuntime",
    "ModelCapabilities",
    "RGBFrame",
    "RobotObservation",
    "Trajectory2D",
    "Vec2",
    "WAMAdapter",
]
