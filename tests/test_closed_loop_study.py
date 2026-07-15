from pathlib import Path

import pytest

from wamprobe.cli import main
from wamprobe.closed_loop import run_closed_loop_study


def test_closed_loop_replanning_separates_oracle_from_action_ignorance() -> None:
    study = run_closed_loop_study(
        benchmark_names=("blockpush",),
        contexts=4,
        seed=5,
        execute_prefix=1,
        resamples=64,
    )
    result = study.benchmarks[0]
    profiles = {profile.controller_id: profile for profile in result.profiles}

    oracle = profiles["oracle-simulator"]
    copy_last = profiles["copy-last-frame"]
    assert oracle.success_summary.mean == 1.0
    assert oracle.return_summary.mean > copy_last.return_summary.mean
    assert oracle.offline_crc_spearman == 1.0
    assert copy_last.offline_crc_spearman == 0.0
    assert all(len(episode.selected_actions) == result.control_steps for episode in oracle.episodes)
    assert result.correlations["offline_crc_vs_closed_loop_return_pearson"] is not None
    assert result.correlations["offline_crc_vs_closed_loop_return_pearson"] > 0.0


def test_closed_loop_study_is_deterministic_and_validates_execution_budget() -> None:
    first = run_closed_loop_study(
        benchmark_names=("gripper-catch",),
        contexts=3,
        seed=11,
        execute_prefix=1,
        resamples=32,
    )
    second = run_closed_loop_study(
        benchmark_names=("gripper-catch",),
        contexts=3,
        seed=11,
        execute_prefix=1,
        resamples=32,
    )
    assert first.to_dict() == second.to_dict()

    with pytest.raises(ValueError, match="execute_prefix"):
        run_closed_loop_study(
            benchmark_names=("blockpush",),
            contexts=2,
            execute_prefix=7,
        )


def test_closed_loop_study_cli_writes_structured_reports(tmp_path: Path) -> None:
    assert (
        main(
            [
                "closed-loop-study",
                "--benchmark",
                "blockpush",
                "--contexts",
                "2",
                "--seed",
                "5",
                "--resamples",
                "32",
                "--output",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert (tmp_path / "closed-loop-study.json").is_file()
    report = (tmp_path / "closed-loop-study.md").read_text(encoding="utf-8")
    assert "oracle-simulator" in report
    assert "offline CRC" in report
