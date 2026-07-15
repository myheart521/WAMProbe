import json
from pathlib import Path

import pytest

from wamprobe.cli import main
from wamprobe.experiments import analyze_action_experiment


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
    predictions = tmp_path / "predictions"
    predictions.mkdir()
    matrix_records: list[dict[str, object]] = []
    execution_records: list[dict[str, object]] = []
    for nfe in (1, 4):
        for seed in (0, 1):
            cache_key = f"{nfe}{seed}".ljust(64, "a")
            action_value = 0.01 * nfe + 0.02 * seed
            actions = [
                [action_value, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0],
                [action_value * 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0],
            ]
            (predictions / f"{cache_key}.json").write_text(
                json.dumps(
                    {
                        "cache_key": cache_key,
                        "prediction": {
                            "actions": actions,
                            "runtime": {
                                "latency_seconds": float(nfe) / 10.0 + seed / 100.0,
                                "peak_allocated_bytes": nfe * 1024**3,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            matrix_records.append(
                {
                    "task_key": "task-a",
                    "seed": seed,
                    "num_inference_steps": nfe,
                    "cache_key": cache_key,
                    "status": "generated",
                }
            )
            displacement = action_value * nfe
            checkpoints = {
                "1": {
                    "eef_position": [displacement, 0.0, 0.0],
                    "cumulative_return": 0.0,
                    "success": False,
                },
                "2": {
                    "eef_position": [displacement * 2.0, 0.0, 0.0],
                    "cumulative_return": float(seed == 1 and nfe == 4),
                    "success": seed == 1 and nfe == 4,
                },
            }
            execution_records.append(
                {
                    "cache_key": cache_key,
                    "outcome": {
                        "initial_eef_position": [0.0, 0.0, 0.0],
                        "checkpoints": checkpoints,
                    },
                }
            )
    matrix_path = tmp_path / "matrix-index.json"
    matrix_path.write_text(
        json.dumps(
            {
                "model_id": "model-a",
                "benchmark_id": "benchmark-a",
                "failed_predictions": 0,
                "capability_skips": [
                    {"ablation": "action-mask", "reason": "unsupported capability"}
                ],
                "records": matrix_records,
            }
        ),
        encoding="utf-8",
    )
    execution_path = tmp_path / "execution-index.json"
    execution_path.write_text(
        json.dumps({"failed_tasks": [], "records": execution_records}),
        encoding="utf-8",
    )
    return matrix_path, execution_path


def test_action_experiment_aligns_matrix_and_reports_sensitivity(tmp_path: Path) -> None:
    matrix, execution = _write_fixture(tmp_path)

    analysis = analyze_action_experiment(matrix, execution)

    assert analysis.predictions == 4
    assert [summary.num_inference_steps for summary in analysis.efficiency] == [1, 4]
    assert analysis.efficiency[0].mean_latency_seconds == pytest.approx(0.105)
    assert analysis.horizons[-1].success_rate == pytest.approx(0.25)
    assert analysis.seed_sensitivity.groups == 2
    assert analysis.seed_sensitivity.pairs == 2
    assert analysis.nfe_sensitivity.groups == 2
    assert analysis.nfe_sensitivity.pairs == 2
    assert analysis.correlations["nfe_vs_latency_pearson"] is not None
    assert len(analysis.skipped_analyses) == 3


def test_experiment_report_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    matrix, execution = _write_fixture(tmp_path)
    output = tmp_path / "report"

    assert (
        main(
            [
                "experiment-report",
                str(matrix),
                str(execution),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    payload = json.loads((output / "experiment.json").read_text(encoding="utf-8"))
    assert payload["predictions"] == 4
    assert "Capability-gated" in (output / "experiment.md").read_text(encoding="utf-8")
