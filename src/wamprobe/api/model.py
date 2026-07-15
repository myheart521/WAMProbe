"""Protocol implemented by World Action Model adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from wamprobe.api.capabilities import ModelCapabilities
from wamprobe.api.robotics import ActionPrediction, RobotObservation
from wamprobe.api.types import Action2D, Context2D, Trajectory2D


@runtime_checkable
class WAMAdapter(Protocol):
    """Minimal state-future adapter used by the CPU-first MVP."""

    @property
    def capabilities(self) -> ModelCapabilities:
        """Describe outputs and runtime behavior exposed by the adapter."""

        ...

    def predict_future(
        self,
        context: Context2D,
        action: Action2D,
        *,
        horizon: int,
        seed: int,
    ) -> Trajectory2D:
        """Predict a future trajectory for one context/action intervention."""

        ...

    def close(self) -> None:
        """Release resources owned by the adapter."""

        ...


@runtime_checkable
class ActionPredictorAdapter(Protocol):
    """Protocol for WAMs that directly emit robot action chunks."""

    @property
    def capabilities(self) -> ModelCapabilities:
        """Describe the action capabilities exposed by the adapter."""

        ...

    def predict_action(
        self,
        observation: RobotObservation,
        *,
        seed: int,
    ) -> ActionPrediction:
        """Predict one semantically typed action chunk."""

        ...

    def close(self) -> None:
        """Release resources owned by the adapter."""

        ...
