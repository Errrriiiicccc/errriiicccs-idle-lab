"""Screenshot the anchored window (or a normalized ROI inside it)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image

from idle_lab.automations.schema import Roi
from idle_lab.models import Rect


class CaptureError(RuntimeError):
    """Screenshot could not be taken."""


def _roi_pixel_box(rect: Rect, roi: Roi) -> tuple[int, int, int, int]:
    """Return inclusive pixel box (left, top, right, bottom) in screen coords."""

    span_x = max(rect.width - 1, 0)
    span_y = max(rect.height - 1, 0)
    left = int(round(rect.left + float(roi.nx) * span_x))
    top = int(round(rect.top + float(roi.ny) * span_y))
    right = int(round(rect.left + float(roi.nx + roi.nw) * span_x))
    bottom = int(round(rect.top + float(roi.ny + roi.nh) * span_y))
    if right < left:
        left, right = right, left
    if bottom < top:
        top, bottom = bottom, top
    return left, top, right, bottom


def grab_rect(rect: Rect) -> Image.Image:
    """Capture a screen rectangle with mss."""

    try:
        import mss
    except ImportError as exc:  # pragma: no cover
        raise CaptureError("mss is not installed") from exc

    width = max(rect.width, 1)
    height = max(rect.height, 1)
    monitor = {"left": rect.left, "top": rect.top, "width": width, "height": height}
    with mss.mss() as sct:
        shot = sct.grab(monitor)
    image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    return image


def grab_anchor(rect: Rect | None) -> Image.Image:
    if rect is None:
        raise CaptureError("anchor missing")
    if rect.width <= 0 or rect.height <= 0:
        raise CaptureError("anchor rect is empty")
    return grab_rect(rect)


def crop_roi(image: Image.Image, rect: Rect, roi: Roi) -> Image.Image:
    left, top, right, bottom = _roi_pixel_box(rect, roi)
    local_left = max(0, left - rect.left)
    local_top = max(0, top - rect.top)
    local_right = min(image.width, right - rect.left + 1)
    local_bottom = min(image.height, bottom - rect.top + 1)
    if local_right <= local_left or local_bottom <= local_top:
        raise CaptureError(f"roi {roi.id} is outside the capture")
    return image.crop((local_left, local_top, local_right, local_bottom))


def save_screenshot(image: Image.Image, folder: Path, prefix: str = "shot") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = folder / f"{prefix}_{stamp}.png"
    image.save(path)
    return path
