"""Browse finished Observation Lab (User) batches on disk."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from idle_lab.screen_map.manifest import Manifest, ShotRecord, load_manifest, manifest_path

GROUP_TODAY = "Today"
GROUP_YESTERDAY = "Yesterday"
GROUP_LAST_7 = "Last 7 Days"
GROUP_THE_PAST = "The Past"
GROUP_ORDER = (GROUP_TODAY, GROUP_YESTERDAY, GROUP_LAST_7, GROUP_THE_PAST)


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


def _batch_day(created_at: str) -> date | None:
    raw = str(created_at or "").strip()
    if not raw:
        return None
    try:
        # ISO date or datetime
        if "T" in raw:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def catalog_group_for(created_at: str, *, today: date | None = None) -> str:
    """Map a batch timestamp into Today / Yesterday / Last 7 Days / The Past."""

    day = _batch_day(created_at)
    if day is None:
        return GROUP_THE_PAST
    now = today or date.today()
    if day == now:
        return GROUP_TODAY
    if day == now - timedelta(days=1):
        return GROUP_YESTERDAY
    if now - timedelta(days=6) <= day < now:
        return GROUP_LAST_7
    return GROUP_THE_PAST


def group_batches(
    batches: list[BatchSummary],
    *,
    today: date | None = None,
) -> list[tuple[str, list[BatchSummary]]]:
    buckets: dict[str, list[BatchSummary]] = {name: [] for name in GROUP_ORDER}
    for batch in batches:
        buckets[catalog_group_for(batch.created_at, today=today)].append(batch)
    return [(name, buckets[name]) for name in GROUP_ORDER if buckets[name]]
