from pathlib import Path

import pytest

from wamprobe.api.robotics import RGBFrame
from wamprobe.cli import main
from wamprobe.video_control_study import run_video_control_study
from wamprobe.video_metrics import invert_rgb, rgb_global_ssim, rgb_psnr


def test_rgb_fidelity_metrics_distinguish_exact_and_inverted_frames() -> None:
    frame = RGBFrame("camera", 2, 1, bytes((0, 64, 128, 255, 192, 127)))
    inverted = invert_rgb(frame)

    assert rgb_psnr(frame, frame) == 100.0
    assert rgb_global_ssim(frame, frame) == pytest.approx(1.0)
    assert rgb_psnr(inverted, frame) < 10.0
    assert rgb_global_ssim(inverted, frame) < 0.0


def test_video_control_study_exposes_appearance_control_counterexample() -> None:
    study = run_video_control_study(
        benchmark_names=("blockpush",),
        contexts=4,
        seed=5,
    )
    result = study.benchmarks[0]
    profiles = {profile.model_id: profile for profile in result.profiles}

    oracle = profiles["oracle-simulator"]
    corrupted = profiles["appearance-corrupted-oracle"]
    assert corrupted.top1_regret == oracle.top1_regret == 0.0
    assert corrupted.state_fde == oracle.state_fde == 0.0
    assert corrupted.mean_psnr_db < oracle.mean_psnr_db
    assert result.psnr_regret_order_disagreements > 0


def test_video_control_study_cli_writes_reports(tmp_path: Path) -> None:
    assert (
        main(
            [
                "video-control-study",
                "--benchmark",
                "blockpush",
                "--contexts",
                "4",
                "--seed",
                "5",
                "--output",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert (tmp_path / "video-control-study.json").is_file()
    assert "appearance-corrupted-oracle" in (tmp_path / "video-control-study.md").read_text(
        encoding="utf-8"
    )
