"""Machine- and human-readable report generation."""

from __future__ import annotations

import json
from pathlib import Path

from wamprobe.evaluation import EvaluationResult

_METRIC_COLUMNS = (
    ("action_dependence", "Action Dependence"),
    ("counterfactual_direction_accuracy", "Counterfactual Direction"),
    ("noop_stability", "No-op Stability"),
    ("state_ade", "State ADE ↓"),
    ("top1_regret", "Top-1 Regret ↓"),
)


def render_markdown(results: list[EvaluationResult]) -> str:
    """Render a compact comparison table."""

    headers = ["Model", *(label for _, label in _METRIC_COLUMNS)]
    lines = [
        "# WAMProbe PointMass-2D Demo",
        "",
        "This report compares action-aware and deliberately broken reference baselines.",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for result in results:
        values = [result.model_id]
        values.extend(f"{result.metrics[key]:.4f}" for key, _ in _METRIC_COLUMNS)
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            "A high Action Dependence score is not sufficient: the wrong-direction baseline",
            "depends on the action but fails Counterfactual Direction Accuracy. This is why",
            "WAMProbe reports a metric profile instead of a single aggregate score.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    output_dir: Path,
    *,
    benchmark: str,
    results: list[EvaluationResult],
) -> tuple[Path, Path]:
    """Write versioned JSON and Markdown reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    report_path = output_dir / "report.md"
    payload = {
        "schema_version": "0.1",
        "benchmark": benchmark,
        "results": [result.to_dict() for result in results],
    }
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_markdown(results), encoding="utf-8")
    return summary_path, report_path
