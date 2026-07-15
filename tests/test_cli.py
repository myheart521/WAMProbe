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
    assert summary_path.is_file()
    assert report_path.is_file()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["benchmark"] == "pointmass-2d-v0.1"
    assert {result["model_id"] for result in summary["results"]} == {
        "action-agnostic",
        "copy-last-frame",
        "oracle-pointmass",
        "wrong-direction",
    }
    assert "Counterfactual Direction" in report_path.read_text(encoding="utf-8")
    assert "WAMProbe demo complete" in capsys.readouterr().out
