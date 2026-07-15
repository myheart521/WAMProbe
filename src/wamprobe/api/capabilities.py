"""Machine-readable model capability declarations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class FutureRepresentation(StrEnum):
    """Representations a WAM may expose for predicted futures."""

    NONE = "none"
    PIXELS = "pixels"
    STATES = "states"
    LATENTS = "latents"


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    """Capabilities used to route only compatible WAMProbe metrics."""

    model_id: str
    future_representation: FutureRepresentation
    predicts_actions: bool = False
    scores_actions: bool = False
    exposes_world_features: bool = False
    stochastic: bool = False
    deterministic_seed: bool = True
    supports_batching: bool = False

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        result = asdict(self)
        result["future_representation"] = self.future_representation.value
        return result
