"""OpenCV template matching for icon presence (optional dependency)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


class TemplateMatchError(RuntimeError):
    """Template matching failed or OpenCV is unavailable."""


@dataclass(frozen=True)
class TemplateMatchResult:
    present: bool
    score: float
    threshold: float
    x: int
    y: int
    template_path: str


def opencv_available() -> bool:
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401

        return True
    except ImportError:
        return False


def resolve_template_path(templates_dir: Path, template_id: str) -> Path:
    name = str(template_id).strip()
    if not name:
        raise TemplateMatchError("template id is empty")
    direct = Path(name)
    if direct.is_file():
        return direct
    templates_dir = Path(templates_dir)
    candidate = templates_dir / name
    if candidate.is_file():
        return candidate
    stem = name
    for suffix in (".png", ".PNG", ".jpg", ".jpeg", ".JPG", ".JPEG"):
        if name.lower().endswith(suffix.lower()):
            stem = name[: -len(suffix)]
            break
    for suffix in (".png", ".PNG", ".jpg", ".jpeg"):
        path = templates_dir / f"{stem}{suffix}"
        if path.is_file():
            return path
    raise TemplateMatchError(f"template not found: {name} (looked in {templates_dir})")


def match_template(
    scene: Image.Image,
    template_path: Path,
    *,
    threshold: float = 0.85,
) -> TemplateMatchResult:
    if not opencv_available():
        raise TemplateMatchError(
            "OpenCV not installed — pip install opencv-python-headless (OCR still works without it)"
        )
    import cv2
    import numpy as np

    scene_rgb = scene.convert("RGB")
    scene_arr = np.array(scene_rgb)[:, :, ::-1]  # RGB → BGR
    template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if template is None:
        raise TemplateMatchError(f"could not read template image: {template_path}")
    th, tw = template.shape[:2]
    sh, sw = scene_arr.shape[:2]
    if th > sh or tw > sw:
        raise TemplateMatchError(
            f"template {tw}x{th} larger than search region {sw}x{sh} — re-crop or widen ROI"
        )
    result = cv2.matchTemplate(scene_arr, template, cv2.TM_CCOEFF_NORMED)
    _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
    score = float(max_val)
    x = int(max_loc[0] + tw / 2)
    y = int(max_loc[1] + th / 2)
    return TemplateMatchResult(
        present=score >= float(threshold),
        score=score,
        threshold=float(threshold),
        x=x,
        y=y,
        template_path=str(template_path),
    )
