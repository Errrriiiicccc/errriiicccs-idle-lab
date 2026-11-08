"""Batch folder + screenshot-mode state machine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from PIL import Image

from idle_lab.screen_map.manifest import Manifest, ShotRecord, append_shot, new_manifest, save_manifest
from idle_lab.screen_map.names import sanitize_slug, unique_dir


class Mode(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    TITLE_DIALOG = "title_dialog"


class ScreenMapError(RuntimeError):
    """User-facing Screen Map failure."""


@dataclass
class BatchSession:
    folder: Path
    manifest: Manifest

    @property
    def shot_count(self) -> int:
        return len(self.manifest.shots)

    @property
    def titles(self) -> list[str]:
        return [shot.title for shot in self.manifest.shots]


def create_batch(root: Path, batch_title: str) -> BatchSession:
    title = (batch_title or "").strip()
    if not title:
        raise ScreenMapError("Batch title is required.")
    slug = sanitize_slug(title, fallback="batch")
    folder = unique_dir(root, slug)
    folder.mkdir(parents=True, exist_ok=False)
    manifest = new_manifest(title, folder.name)
    save_manifest(folder, manifest)
    return BatchSession(folder=folder, manifest=manifest)


def add_shot(
    session: BatchSession,
    *,
    title: str,
    image: Image.Image,
    anchor: dict[str, Any] | None,
    image_format: str = "png",
    jpeg_quality: int = 70,
) -> ShotRecord:
    human = (title or "").strip()
    if not human:
        raise ScreenMapError("Screenshot title is required.")
    index = session.shot_count + 1
    shot_slug = sanitize_slug(human, fallback="shot")
    fmt = (image_format or "png").strip().lower()
    ext = "jpg" if fmt in {"jpg", "jpeg"} else "png"
    filename = f"{index:02d}_{shot_slug}.{ext}"
    path = session.folder / filename
    # Avoid rare collisions if the same title is reused with a different index padding edge case.
    if path.exists():
        filename = f"{index:02d}_{shot_slug}_{index}.{ext}"
        path = session.folder / filename
    if ext == "jpg":
        image.convert("RGB").save(path, format="JPEG", quality=int(jpeg_quality), optimize=True)
    else:
        image.save(path)
    shot = ShotRecord(
        index=index,
        title=human,
        filename=filename,
        captured_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        anchor=anchor,
        classification=None,
        how_opened=None,
        notes=None,
    )
    session.manifest = append_shot(session.manifest, shot)
    save_manifest(session.folder, session.manifest)
    return shot


class ScreenMapController:
    """Unit-testable mode transitions for screenshot batching."""

    def __init__(self) -> None:
        self.mode = Mode.IDLE
        self.session: BatchSession | None = None

    @property
    def active(self) -> bool:
        return self.mode != Mode.IDLE

    @property
    def dialog_open(self) -> bool:
        return self.mode == Mode.TITLE_DIALOG

    def start(self, session: BatchSession) -> None:
        if self.mode != Mode.IDLE:
            raise ScreenMapError("A batch is already in progress.")
        self.session = session
        self.mode = Mode.ACTIVE

    def begin_title_dialog(self) -> None:
        if self.mode != Mode.ACTIVE:
            raise ScreenMapError("Screenshot mode is not active.")
        self.mode = Mode.TITLE_DIALOG

    def cancel_title_dialog(self) -> None:
        if self.mode != Mode.TITLE_DIALOG:
            return
        self.mode = Mode.ACTIVE

    def finish_title_dialog(self) -> None:
        if self.mode != Mode.TITLE_DIALOG:
            raise ScreenMapError("No title dialog is open.")
        self.mode = Mode.ACTIVE

    def end(self) -> BatchSession | None:
        session = self.session
        self.session = None
        self.mode = Mode.IDLE
        return session
