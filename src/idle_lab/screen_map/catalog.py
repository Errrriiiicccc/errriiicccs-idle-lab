"""Browse finished Screen Map batches on disk."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from idle_lab.screen_map.manifest import Manifest, ShotRecord, load_manifest, manifest_path


@dataclass
class BatchSummary:
    folder: Path
    slug: str
    title: str
    created_at: str
    shot_count: int
    manifest: Manifest

    @property
    def shot_titles(self) -> list[str]:
        return [shot.title for shot in self.manifest.shots]

    def shot_path(self, shot: ShotRecord) -> Path:
        return self.folder / shot.filename


def list_batches(root: Path) -> list[BatchSummary]:
    root = Path(root)
    if not root.exists():
        return []
    out: list[BatchSummary] = []
    for folder in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not folder.is_dir():
            continue
        if not manifest_path(folder).exists():
            continue
        try:
            manifest = load_manifest(folder)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        out.append(
            BatchSummary(
                folder=folder,
                slug=folder.name,
                title=manifest.batch_title or folder.name,
                created_at=manifest.created_at,
                shot_count=len(manifest.shots),
                manifest=manifest,
            )
        )
    # Newest first by created_at then name.
    out.sort(key=lambda item: (item.created_at or "", item.slug), reverse=True)
    return out
