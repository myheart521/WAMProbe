"""Dependency-free diagnostic RGB fidelity metrics."""

from __future__ import annotations

import math

from wamprobe.api.robotics import RGBFrame


def _validate_pair(predicted: RGBFrame, truth: RGBFrame) -> None:
    if (
        predicted.height != truth.height
        or predicted.width != truth.width
        or predicted.camera_name != truth.camera_name
    ):
        raise ValueError("RGB metric inputs must have matching camera names and shapes")


def rgb_psnr(predicted: RGBFrame, truth: RGBFrame, *, exact_cap: float = 100.0) -> float:
    """Return RGB PSNR in dB, using a finite cap for exact uint8 matches."""

    _validate_pair(predicted, truth)
    if not math.isfinite(exact_cap) or exact_cap <= 0:
        raise ValueError("exact_cap must be finite and positive")
    squared_error = sum(
        (predicted_value - truth_value) ** 2
        for predicted_value, truth_value in zip(predicted.data, truth.data, strict=True)
    )
    if squared_error == 0:
        return exact_cap
    mse = squared_error / len(predicted.data)
    return 10.0 * math.log10(255.0**2 / mse)


def _channel_values(frame: RGBFrame, channel: int) -> list[float]:
    return [float(value) for value in frame.data[channel::3]]


def rgb_global_ssim(predicted: RGBFrame, truth: RGBFrame) -> float:
    """Return mean per-channel global SSIM without claiming windowed SSIM parity."""

    _validate_pair(predicted, truth)
    channel_scores: list[float] = []
    c1 = (0.01 * 255.0) ** 2
    c2 = (0.03 * 255.0) ** 2
    for channel in range(3):
        left = _channel_values(predicted, channel)
        right = _channel_values(truth, channel)
        left_mean = sum(left) / len(left)
        right_mean = sum(right) / len(right)
        left_variance = sum((value - left_mean) ** 2 for value in left) / len(left)
        right_variance = sum((value - right_mean) ** 2 for value in right) / len(right)
        covariance = sum(
            (left_value - left_mean) * (right_value - right_mean)
            for left_value, right_value in zip(left, right, strict=True)
        ) / len(left)
        score = ((2.0 * left_mean * right_mean + c1) * (2.0 * covariance + c2)) / (
            (left_mean**2 + right_mean**2 + c1) * (left_variance + right_variance + c2)
        )
        channel_scores.append(score)
    return sum(channel_scores) / len(channel_scores)


def invert_rgb(frame: RGBFrame) -> RGBFrame:
    """Return a deterministic appearance corruption for metric sanity tests."""

    return RGBFrame(
        camera_name=frame.camera_name,
        height=frame.height,
        width=frame.width,
        data=bytes(255 - value for value in frame.data),
    )
