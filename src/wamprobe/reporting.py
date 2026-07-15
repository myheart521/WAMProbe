"""Machine- and human-readable report generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from html import escape
from pathlib import Path

from wamprobe.evaluation import EvaluationResult
from wamprobe.stats import MetricSummary, PairedComparison, paired_metric_comparison, summarize

_METRIC_COLUMNS = (
    ("action_dependence", "Action Dependence"),
    ("action_dependence_permutation_effect", "Permutation Effect"),
    ("action_dependence_permutation_p_value", "Permutation p-value ↓"),
    ("counterfactual_direction_accuracy", "Counterfactual Direction"),
    ("noop_stability", "No-op Stability"),
    ("state_ade", "State ADE ↓"),
    ("state_fde", "State FDE ↓"),
    ("candidate_ranking_spearman", "CRC Spearman"),
    ("candidate_ranking_kendall_tau", "CRC Kendall τ"),
    ("candidate_ranking_ndcg", "CRC NDCG"),
    ("candidate_ranking_pairwise_accuracy", "CRC Pairwise Accuracy"),
    ("top1_regret", "Top-1 Regret ↓"),
)

StatisticsByModel = dict[str, dict[str, MetricSummary]]


def _report_title(results: list[EvaluationResult]) -> str:
    benchmark = results[0].benchmark if results else "evaluation"
    return f"WAMProbe {benchmark} Demo"


def _stable_seed(seed: int, *parts: str) -> int:
    material = "\0".join((str(seed), *parts)).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _build_statistics(
    results: list[EvaluationResult],
    *,
    resamples: int,
    seed: int,
) -> tuple[StatisticsByModel, list[PairedComparison]]:
    statistics: StatisticsByModel = {}
    for result in results:
        model_statistics: dict[str, MetricSummary] = {}
        for metric, _ in _METRIC_COLUMNS:
            values = tuple(context.metrics[metric] for context in result.context_results)
            model_statistics[metric] = summarize(
                values,
                resamples=resamples,
                seed=_stable_seed(seed, result.model_id, metric),
            )
        statistics[result.model_id] = model_statistics

    comparisons: list[PairedComparison] = []
    if len(results) > 1:
        reference = next(
            (result for result in results if result.model_id == "oracle-pointmass"),
            results[0],
        )
        for result in results:
            if result is reference:
                continue
            for metric, _ in _METRIC_COLUMNS:
                comparisons.append(
                    paired_metric_comparison(
                        reference,
                        result,
                        metric=metric,
                        resamples=resamples,
                        seed=_stable_seed(seed, reference.model_id, result.model_id, metric),
                    )
                )
    return statistics, comparisons


def render_markdown(
    results: list[EvaluationResult],
    *,
    statistics: StatisticsByModel | None = None,
    comparisons: list[PairedComparison] | None = None,
) -> str:
    """Render a comparison table and context-block uncertainty estimates."""

    headers = ["Model", *(label for _, label in _METRIC_COLUMNS)]
    lines = [
        f"# {_report_title(results)}",
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

    if statistics:
        lines.extend(
            [
                "",
                "## Context-block 95% confidence intervals",
                "",
                "Intervals resample whole contexts, not correlated action branches or frames.",
                "",
                "| Model | Metric | Mean | 95% CI | Median | Std |",
                "|---|---|---:|---:|---:|---:|",
            ]
        )
        for result in results:
            for metric, label in _METRIC_COLUMNS:
                summary = statistics[result.model_id][metric]
                interval = summary.confidence_interval
                lines.append(
                    f"| {result.model_id} | {label} | {summary.mean:.4f} | "
                    f"[{interval.lower:.4f}, {interval.upper:.4f}] | "
                    f"{summary.median:.4f} | {summary.standard_deviation:.4f} |"
                )

    if comparisons:
        lines.extend(
            [
                "",
                "## Paired model differences",
                "",
                "Differences are left minus right over exactly aligned context IDs.",
                "",
                "| Models | Metric | Mean difference | 95% CI | Contexts |",
                "|---|---|---:|---:|---:|",
            ]
        )
        labels = dict(_METRIC_COLUMNS)
        for comparison in comparisons:
            interval = comparison.confidence_interval
            lines.append(
                f"| {comparison.left_model} − {comparison.right_model} | "
                f"{labels[comparison.metric]} | {comparison.mean_difference:.4f} | "
                f"[{interval.lower:.4f}, {interval.upper:.4f}] | "
                f"{comparison.contexts} |"
            )

    lines.extend(
        [
            "",
            "Action separation alone does not establish correct direction, state dynamics,",
            "or control ranking. WAMProbe therefore reports a metric profile rather than a",
            "single composite score.",
            "",
        ]
    )
    return "\n".join(lines)


def render_html(
    results: list[EvaluationResult],
    *,
    statistics: StatisticsByModel,
    comparisons: list[PairedComparison],
) -> str:
    """Render a standalone, dependency-free HTML report."""

    title = _report_title(results)
    metric_headers = "".join(f"<th>{escape(label)}</th>" for _, label in _METRIC_COLUMNS)
    result_rows: list[str] = []
    for result in results:
        cells = "".join(f"<td>{result.metrics[metric]:.4f}</td>" for metric, _ in _METRIC_COLUMNS)
        result_rows.append(f"<tr><th>{escape(result.model_id)}</th>{cells}</tr>")

    statistic_rows: list[str] = []
    for result in results:
        for metric, label in _METRIC_COLUMNS:
            summary = statistics[result.model_id][metric]
            interval = summary.confidence_interval
            statistic_rows.append(
                "<tr>"
                f"<th>{escape(result.model_id)}</th>"
                f"<td>{escape(label)}</td>"
                f"<td>{summary.mean:.4f}</td>"
                f"<td>[{interval.lower:.4f}, {interval.upper:.4f}]</td>"
                f"<td>{summary.median:.4f}</td>"
                f"<td>{summary.standard_deviation:.4f}</td>"
                f"<td>{summary.quantiles['p05']:.4f} / {summary.quantiles['p95']:.4f}</td>"
                "</tr>"
            )

    labels = dict(_METRIC_COLUMNS)
    comparison_rows = "".join(
        "<tr>"
        f"<th>{escape(comparison.left_model)} − {escape(comparison.right_model)}</th>"
        f"<td>{escape(labels[comparison.metric])}</td>"
        f"<td>{comparison.mean_difference:.4f}</td>"
        f"<td>[{comparison.confidence_interval.lower:.4f}, "
        f"{comparison.confidence_interval.upper:.4f}]</td>"
        f"<td>{comparison.contexts}</td>"
        "</tr>"
        for comparison in comparisons
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0 auto; max-width: 1480px; padding: 2rem; color: #172033;
      background: #f5f7fb; }}
    h1, h2 {{ letter-spacing: -0.02em; }}
    section {{ margin: 1.4rem 0; padding: 1.2rem; border: 1px solid #d9dfeb;
      border-radius: 12px; background: white; box-shadow: 0 3px 14px #1720330d; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }}
    th, td {{ padding: .65rem .75rem; border-bottom: 1px solid #e7eaf0; text-align: right; }}
    th:first-child, td:first-child, td:nth-child(2) {{ text-align: left; white-space: nowrap; }}
    thead th {{ color: #47546c; font-size: .82rem; }}
    .note {{ color: #56637a; line-height: 1.55; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <p class="note">Action-aware and deliberately broken baselines are shown as a metric
  profile. No composite score is produced.</p>
  <section>
    <h2>Metric profile</h2>
    <div class="table-wrap"><table>
      <thead><tr><th>Model</th>{metric_headers}</tr></thead>
      <tbody>{"".join(result_rows)}</tbody>
    </table></div>
  </section>
  <section>
    <h2>Context-block 95% confidence intervals</h2>
    <p class="note">Whole contexts are resampled; correlated branches and frames are never
    treated as independent observations.</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Model</th><th>Metric</th><th>Mean</th><th>95% CI</th>
      <th>Median</th><th>Std</th><th>p05 / p95</th></tr></thead>
      <tbody>{"".join(statistic_rows)}</tbody>
    </table></div>
  </section>
  <section>
    <h2>Paired model differences</h2>
    <p class="note">Each value is left minus right, aligned by exact context ID.</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Models</th><th>Metric</th><th>Mean difference</th>
      <th>95% CI</th><th>Contexts</th></tr></thead>
      <tbody>{comparison_rows}</tbody>
    </table></div>
  </section>
</body>
</html>
"""


def write_reports(
    output_dir: Path,
    *,
    benchmark: str,
    results: list[EvaluationResult],
    resamples: int = 1000,
    seed: int = 0,
) -> tuple[Path, Path, Path]:
    """Write versioned JSON, Markdown, and standalone HTML reports."""

    if not results:
        raise ValueError("at least one evaluation result is required")
    if any(result.benchmark != benchmark for result in results):
        raise ValueError("all evaluation results must match the report benchmark")
    statistics, comparisons = _build_statistics(results, resamples=resamples, seed=seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    report_path = output_dir / "report.md"
    html_path = output_dir / "report.html"
    jsonl_path = output_dir / "results.jsonl"
    payload = {
        "schema_version": "0.1",
        "benchmark": benchmark,
        "results": [result.to_dict() for result in results],
        "statistics": {
            model_id: {metric: asdict(summary) for metric, summary in metrics.items()}
            for model_id, metrics in statistics.items()
        },
        "paired_comparisons": [asdict(comparison) for comparison in comparisons],
    }
    summary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        render_markdown(results, statistics=statistics, comparisons=comparisons),
        encoding="utf-8",
    )
    html_path.write_text(
        render_html(results, statistics=statistics, comparisons=comparisons),
        encoding="utf-8",
    )
    jsonl_records = (
        {
            "schema_version": "0.1",
            "benchmark": result.benchmark,
            "model_id": result.model_id,
            "context_id": context.context_id,
            "selected_action": context.selected_action,
            "optimal_action": context.optimal_action,
            "top1_regret": context.top1_regret,
            "metrics": context.metrics,
        }
        for result in results
        for context in result.context_results
    )
    jsonl_path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in jsonl_records
        ),
        encoding="utf-8",
    )
    return summary_path, report_path, html_path
