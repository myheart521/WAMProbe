import json
from pathlib import Path

import pytest

from wamprobe.cli import main


def test_demo_cli_writes_machine_and_human_readable_reports(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "demo",
            "--contexts",
            "5",
            "--seed",
            "9",
            "--output",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    summary_path = tmp_path / "summary.json"
    report_path = tmp_path / "report.md"
    html_path = tmp_path / "report.html"
    assert summary_path.is_file()
    assert report_path.is_file()
    assert html_path.is_file()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["benchmark"] == "pointmass-2d-v0.1"
    assert {result["model_id"] for result in summary["results"]} == {
        "action-agnostic",
        "copy-last-frame",
        "noisy-linear",
        "oracle-pointmass",
        "wrong-direction",
    }
    assert summary["statistics"]
    assert summary["paired_comparisons"]
    assert "Counterfactual Direction" in report_path.read_text(encoding="utf-8")
    html = html_path.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "Context-block 95% confidence intervals" in html
    assert "WAMProbe demo complete" in capsys.readouterr().out
