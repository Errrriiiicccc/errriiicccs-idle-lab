"""Record short clips of the anchored window via mss + ffmpeg."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from idle_lab.automations.capture import CaptureError, grab_rect
from idle_lab.models import Rect


class VideoError(RuntimeError):
    """Clip recording failed."""


def find_ffmpeg() -> str | None:
    env = os.environ.get("FFMPEG_CMD") or os.environ.get("FFMPEG_PATH")
    if env:
        path = Path(env)
        if path.is_dir():
            path = path / "ffmpeg.exe"
        if path.is_file():
            return str(path)

    which = shutil.which("ffmpeg")
    if which:
        return which

    local = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if local.is_dir():
        matches = sorted(local.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"))
        if matches:
            return str(matches[-1])
    for candidate in (
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def ffmpeg_available() -> bool:
    return find_ffmpeg() is not None


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
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise VideoError(
            "ffmpeg not found on PATH. Install with: winget install --id Gyan.FFmpeg -e "
            "Then restart Idle Lab."
        )

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
        # libx264 requires even width/height; window rects are often odd.
        # Scale/crop to nearest even size so encode does not leave a 0-byte mp4.
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-framerate",
            str(fps),
            "-i",
            pattern,
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except OSError as exc:
            _remove_empty(dest)
            raise VideoError(f"ffmpeg failed to start: {exc}") from exc
        if completed.returncode != 0:
            _remove_empty(dest)
            detail = (completed.stderr or completed.stdout or "").strip()
            raise VideoError(detail or "ffmpeg encoding failed")

    if not dest.exists() or dest.stat().st_size <= 0:
        _remove_empty(dest)
        raise VideoError("ffmpeg did not produce a usable output file")
    return dest


def _remove_empty(path: Path) -> None:
    try:
        if path.exists() and path.stat().st_size <= 0:
            path.unlink()
    except OSError:
        pass
