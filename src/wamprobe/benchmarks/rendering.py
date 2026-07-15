"""Small dependency-free rasterizer for analytic manipulation observations."""

from __future__ import annotations

from wamprobe.api.robotics import RGBFrame
from wamprobe.api.types import Vec2

Color = tuple[int, int, int]


def _pixel_coordinate(position: Vec2, *, size: int) -> tuple[int, int]:
    column = round((position.x + 0.6) / 1.2 * (size - 1))
    row = round((0.6 - position.y) / 1.2 * (size - 1))
    return max(0, min(size - 1, column)), max(0, min(size - 1, row))


def _draw_disc(
    pixels: bytearray,
    *,
    size: int,
    center: tuple[int, int],
    radius: int,
    color: Color,
) -> None:
    center_x, center_y = center
    for row in range(max(0, center_y - radius), min(size, center_y + radius + 1)):
        for column in range(max(0, center_x - radius), min(size, center_x + radius + 1)):
            if (column - center_x) ** 2 + (row - center_y) ** 2 > radius**2:
                continue
            offset = (row * size + column) * 3
            pixels[offset : offset + 3] = bytes(color)


def _draw_goal(pixels: bytearray, *, size: int, goal: Vec2) -> None:
    center_x, center_y = _pixel_coordinate(goal, size=size)
    color = (52, 168, 83)
    radius = 5
    for delta in range(-radius, radius + 1):
        for column, row in (
            (center_x + delta, center_y - radius),
            (center_x + delta, center_y + radius),
            (center_x - radius, center_y + delta),
            (center_x + radius, center_y + delta),
        ):
            if 0 <= column < size and 0 <= row < size:
                offset = (row * size + column) * 3
                pixels[offset : offset + 3] = bytes(color)


def render_scene(
    *,
    effector_position: Vec2,
    object_position: Vec2,
    goal: Vec2,
    gripper_closed: bool,
    object_attached: bool,
    size: int = 64,
) -> RGBFrame:
    """Render goal, object, and effector into one tightly packed RGB frame."""

    if size < 16:
        raise ValueError("render size must be at least 16 pixels")
    pixels = bytearray((244, 247, 252) * (size * size))
    _draw_goal(pixels, size=size, goal=goal)
    object_color = (241, 143, 45) if not object_attached else (170, 94, 220)
    _draw_disc(
        pixels,
        size=size,
        center=_pixel_coordinate(object_position, size=size),
        radius=4,
        color=object_color,
    )
    effector_color = (31, 111, 235) if not gripper_closed else (10, 70, 170)
    _draw_disc(
        pixels,
        size=size,
        center=_pixel_coordinate(effector_position, size=size),
        radius=3,
        color=effector_color,
    )
    return RGBFrame("toy-overhead", height=size, width=size, data=bytes(pixels))
