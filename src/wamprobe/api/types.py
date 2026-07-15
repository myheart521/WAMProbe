"""Typed data carried between benchmarks, adapters, and metrics."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True, slots=True)
class Vec2:
    """Small dependency-free two-dimensional vector."""

    x: float
    y: float

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def norm(self) -> float:
        """Return the Euclidean vector norm."""

        return hypot(self.x, self.y)

    def dot(self, other: Vec2) -> float:
        """Return the dot product with another vector."""

        return self.x * other.x + self.y * other.y

    def to_list(self) -> list[float]:
        """Return a JSON-compatible coordinate pair."""

        return [self.x, self.y]


@dataclass(frozen=True, slots=True)
class Context2D:
    """A shared initial state for a counterfactual intervention group."""

    context_id: str
    position: Vec2
    goal: Vec2

    def __post_init__(self) -> None:
        if not self.context_id.strip():
            raise ValueError("context_id must not be empty")


@dataclass(frozen=True, slots=True)
class Action2D:
    """A named per-step displacement intervention."""

    name: str
    delta: Vec2

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("action name must not be empty")


@dataclass(frozen=True, slots=True)
class Trajectory2D:
    """A predicted or ground-truth state trajectory."""

    context_id: str
    action_name: str
    states: tuple[Vec2, ...]

    def __post_init__(self) -> None:
        if not self.states:
            raise ValueError("trajectory must contain at least one state")

    @property
    def final_state(self) -> Vec2:
        """Return the final predicted state."""

        return self.states[-1]


@dataclass(frozen=True, slots=True)
class InterventionGroup:
    """Actions branched from exactly one shared context."""

    context: Context2D
    actions: tuple[Action2D, ...]

    def __post_init__(self) -> None:
        if len(self.actions) < 2:
            raise ValueError("an intervention group requires at least two actions")
        names = [action.name for action in self.actions]
        if len(names) != len(set(names)):
            raise ValueError("action names in an intervention group must be unique")


@dataclass(frozen=True, slots=True)
class InterventionSuite:
    """A versioned collection of counterfactual intervention groups."""

    benchmark_id: str
    groups: tuple[InterventionGroup, ...]

    def __post_init__(self) -> None:
        if not self.benchmark_id.strip():
            raise ValueError("benchmark_id must not be empty")
        if not self.groups:
            raise ValueError("an intervention suite requires at least one group")
