"""Manual screenshot batches for screen mapping."""

from idle_lab.screen_map.batch import BatchSession, ScreenMapController
from idle_lab.screen_map.names import sanitize_slug
from idle_lab.screen_map.manifest import Manifest, ShotRecord, load_manifest, save_manifest

__all__ = [
    "BatchSession",
    "Manifest",
    "ScreenMapController",
    "ShotRecord",
    "load_manifest",
    "sanitize_slug",
    "save_manifest",
]
