"""Record short clips of the anchored window via mss + ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from idle_lab.automations.capture import CaptureError, grab_rect
from idle_lab.models import Rect


class VideoError(RuntimeError):
    """Clip recording failed."""


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def clip_name(run_number: int | str, wave_number: int | str) -> str:
    return f"run_{run_number}_wave_{wave_number}"


def record_clip(
    rect: Rect,
    dest: Path,
    *,
    duration_s: float = 10.0,
    fps: int = 8,
    should_abort=None,
) -> Path:
    """Capture frames for ``duration_s`` and encode to ``dest`` (mp4)."""

    if rect is None:
        raise VideoError("anchor missing")
    if not ffmpeg_available():
        raise VideoError("ffmpeg not found on PATH")

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    frame_interval = 1.0 / max(fps, 1)
    frames: list[Path] = []
    started = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="idle_lab_clip_") as tmp:
        tmp_path = Path(tmp)
        index = 0
        while time.monotonic() - started < duration_s:
            if should_abort and should_abort():
                raise VideoError("recording aborted")
            try:
                image = grab_rect(rect)
            except CaptureError as exc:
                raise VideoError(str(exc)) from exc
            frame_path = tmp_path / f"frame_{index:05d}.png"
            image.save(frame_path)
            frames.append(frame_path)
            index += 1
            elapsed = time.monotonic() - started
            target = index * frame_interval
            sleep_for = target - elapsed
            if sleep_for > 0:
                time.sleep(min(sleep_for, frame_interval))

        if not frames:
            raise VideoError("no frames captured")

        pattern = str(tmp_path / "frame_%05d.png")
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-framerate",
            str(fps),
            "-i",
            pattern,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except OSError as exc:
            raise VideoError(f"ffmpeg failed to start: {exc}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise VideoError(detail or "ffmpeg encoding failed")

    if not dest.exists():
        raise VideoError("ffmpeg did not produce an output file")
    return dest
