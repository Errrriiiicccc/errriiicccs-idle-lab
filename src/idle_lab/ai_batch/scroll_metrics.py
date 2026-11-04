"""Compare consecutive screenshots to decide if a scroll still moved content."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageChops, ImageStat


@dataclass(frozen=True)
class ScrollStepMetric:
    """One scroll attempt and how much the compare ROI changed."""

    step_index: int
    title: str
    mean_abs_diff: float
    changed: bool
    stopped: bool
    stop_reason: str | None = None


def mean_abs_diff(before: Image.Image, after: Image.Image) -> float:
    """Return mean absolute RGB difference in ``[0, 1]`` (0 = identical)."""

    left = before.convert("RGB")
    right = after.convert("RGB")
    if left.size != right.size:
        right = right.resize(left.size, Image.Resampling.BILINEAR)
    diff = ImageChops.difference(left, right)
    stat = ImageStat.Stat(diff)
    # Mean of R,G,B channel means, normalized to 0..1.
    channel_means = stat.mean or [0.0, 0.0, 0.0]
    return max(0.0, min(1.0, (sum(channel_means) / max(len(channel_means), 1)) / 255.0))


def crop_normalized(
    image: Image.Image,
    *,
    nx: float,
    ny: float,
    nw: float,
    nh: float,
) -> Image.Image:
    """Crop a normalized ROI from an already-captured anchor image."""

    width, height = image.size
    left = int(round(max(0.0, min(1.0, nx)) * max(width - 1, 0)))
    top = int(round(max(0.0, min(1.0, ny)) * max(height - 1, 0)))
    right = int(round(max(0.0, min(1.0, nx + nw)) * max(width - 1, 0))) + 1
    bottom = int(round(max(0.0, min(1.0, ny + nh)) * max(height - 1, 0))) + 1
    right = min(width, max(left + 1, right))
    bottom = min(height, max(top + 1, bottom))
    return image.crop((left, top, right, bottom))
