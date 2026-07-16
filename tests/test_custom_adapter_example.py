import json
from pathlib import Path

import pytest

from examples.custom_adapter.adapter import (
    LinearStateBackend,
    PredictionRequest,
    StarterWAMAdapter,
)
from examples.custom_adapter.run import run
from wamprobe.api.capabilities import FutureRepresentation
from wamprobe.api.model import WAMAdapter
from wamprobe.api.types import Action2D, Context2D, Vec2


def test_starter_adapter_is_typed_seeded_and_action_conditioned() -> None:
    adapter = StarterWAMAdapter(LinearStateBackend(), model_id="starter-test")
    context = Context2D("context-0", position=Vec2(0.0, 0.0), goal=Vec2(1.0, 0.0))
    action = Action2D("right", Vec2(0.25, 0.0))

    first = adapter.predict_future(context, action, horizon=4, seed=7)
    second = adapter.predict_future(context, action, horizon=4, seed=7)

    assert isinstance(adapter, WAMAdapter)
    assert adapter.capabilities.model_id == "starter-test"
    assert adapter.capabilities.future_representation is FutureRepresentation.STATES
    assert adapter.capabilities.deterministic_seed is True
    assert first == second
    assert first.context_id == context.context_id
    assert first.action_name == action.name
    assert first.states == (
        Vec2(0.25, 0.0),
        Vec2(0.5, 0.0),
        Vec2(0.75, 0.0),
        Vec2(1.0, 0.0),
    )


def test_starter_adapter_rejects_a_backend_with_the_wrong_horizon() -> None:
    class ShortBackend:
        def predict_positions(
            self,
            request: PredictionRequest,
        ) -> tuple[tuple[float, float], ...]:
            return ((request.position_xy[0], request.position_xy[1]),)

    adapter = StarterWAMAdapter(ShortBackend())
    context = Context2D("context-0", position=Vec2(0.0, 0.0), goal=Vec2(1.0, 0.0))
    action = Action2D("right", Vec2(0.25, 0.0))

    with pytest.raises(ValueError, match="exactly 4 states"):
        adapter.predict_future(context, action, horizon=4, seed=7)


def test_starter_runner_writes_the_standard_report_contract(tmp_path: Path) -> None:
    paths = run(tmp_path, contexts=4, seed=7)

    assert {path.name for path in paths} == {"summary.json", "report.md", "report.html"}
    assert {path.name for path in tmp_path.iterdir()} == {
        "summary.json",
        "results.jsonl",
        "report.md",
        "report.html",
    }
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["benchmark"] == "pointmass-2d-v0.1"
    assert summary["results"][0]["model_id"] == "starter-linear-state"
    assert summary["results"][0]["contexts"] == 4
    assert summary["results"][0]["metrics"]["top1_regret"] == 0.0
