"""Export portable prompt packets for any gen-AI authoring pass."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


PACKET_MD = """# Idle Lab prompt packet

## Identity
You author **Errriiiccc's Idle Lab** automation artifacts only.
Emit JSON files that match the contract below. Prefer filling `description` fields in plain language.
Do not invent action types that are not listed. Do not claim clicks succeeded without Observation evidence.

## Instructions
1. Read `intent/GOAL.md` and the screenshots under `vision/`.
2. Coordinates are **normalized** fractions of the anchored window (`nx`/`ny`/`nw`/`nh` in 0..1).
3. Write outputs under `output/` using the folder layout in this packet.
4. After drafting, mentally validate: every `roi` id exists, every `preset` name exists or is newly created under `output/presets/`.

## Examples
See `contract/fewshot/` for minimal valid samples.

## Context
- Vision manifest: `vision/manifest.json`
- Human goal: `intent/GOAL.md`
- Action catalog: `contract/ACTION_CATALOG.md`
"""

ACTION_CATALOG = """# Action catalog (Idle Lab)

Allowed `type` values on event actions:

| type | Purpose |
| --- | --- |
| screenshot | Grab anchored window; optional `prefix` |
| ocr | Crop `roi`, parse (`raw`/`signal`/`wave`/`currency`/`game_over`/`presence`), set `variable` |
| decide | Branch on variable (`match_a`, `mode`, `on_a`/`on_b`) |
| play_preset / mouse | Play Bench preset by `preset` name |
| wait | Sleep `ms` (prefer wait_until when sensing) |
| wait_until | Poll until variable/ROI/template condition or `timeout_ms` |
| click | `target` or `nx`/`ny` |
| match_template | Icon presence via template id; optional click |
| record_clip | ffmpeg clip `duration_s` |
| csv_append | Append row under runs/ |
| log | Console message with `{variable}` substitution |
| set_variable | Set runtime variable |
| detect_panel | Observe upgrade panel open/tab |
| ensure_upgrade_tab | Open tab only if needed |
| seek_list_top | Scroll list until OCR/`unchanged` |
| scroll_list | Tab-agnostic list scroll (`direction` + `rows`) |

Events need `timing: { "type": "interval", "every_ms": N }` and `priority` (higher wins).
Optional `overdue_policy`: `run_when_free` | `skip` | `run_once_catchup`.
"""

FEWSHOT_EVENT = {
    "id": "example_ab_tick",
    "title": "Example A/B tick",
    "version": 1,
    "enabled": True,
    "priority": 10,
    "timing": {"type": "interval", "every_ms": 10000},
    "description": "OCR a signal ROI and play one of two presets.",
    "actions": [
        {"type": "screenshot", "prefix": "ab", "description": "Capture the anchored window."},
        {
            "type": "ocr",
            "roi": "signal_roi",
            "variable": "signal",
            "parse_as": "signal",
            "description": "Read SIGNAL A/B from the ROI.",
        },
        {
            "type": "decide",
            "variable": "signal",
            "match_a": "A",
            "mode": "equals",
            "explain_a": "play choice A",
            "explain_b": "play choice B",
            "on_a": [{"type": "play_preset", "preset": "ab choice a"}],
            "on_b": [{"type": "play_preset", "preset": "ab choice b"}],
        },
    ],
}

FEWSHOT_ROI = {
    "id": "signal_roi",
    "version": 1,
    "nx": 0.1,
    "ny": 0.1,
    "nw": 0.2,
    "nh": 0.08,
    "notes": "Example SIGNAL band — replace from Screen Map measurements.",
}


def export_prompt_packet(
    dest: Path,
    *,
    goal: str,
    vision_batch_dir: Path | None = None,
    shot_names: list[str] | None = None,
    project_root: Path | None = None,
) -> Path:
    """Create a prompt-packet folder. Returns dest."""

    dest = Path(dest)
    if dest.exists():
        raise FileExistsError(f"packet already exists: {dest}")
    (dest / "contract" / "fewshot").mkdir(parents=True)
    (dest / "vision").mkdir(parents=True)
    (dest / "intent").mkdir(parents=True)
    (dest / "output" / "automations" / "events").mkdir(parents=True)
    (dest / "output" / "automations" / "rois").mkdir(parents=True)
    (dest / "output" / "presets").mkdir(parents=True)

    (dest / "PACKET.md").write_text(PACKET_MD, encoding="utf-8")
    (dest / "contract" / "ACTION_CATALOG.md").write_text(ACTION_CATALOG, encoding="utf-8")
    (dest / "contract" / "fewshot" / "event_example.json").write_text(
        json.dumps(FEWSHOT_EVENT, indent=2), encoding="utf-8"
    )
    (dest / "contract" / "fewshot" / "roi_example.json").write_text(
        json.dumps(FEWSHOT_ROI, indent=2), encoding="utf-8"
    )
    (dest / "intent" / "GOAL.md").write_text(goal.strip() + "\n", encoding="utf-8")

    # Optional schema excerpt from docs
    if project_root is not None:
        schema_doc = Path(project_root) / "docs" / "automation-schema.md"
        if schema_doc.is_file():
            shutil.copy2(schema_doc, dest / "contract" / "automation-schema.md")

    manifest: dict[str, Any] = {
        "version": 1,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "shots": [],
    }
    if vision_batch_dir is not None and Path(vision_batch_dir).is_dir():
        batch = Path(vision_batch_dir)
        src_manifest_path = batch / "manifest.json"
        src_manifest: dict[str, Any] = {}
        if src_manifest_path.is_file():
            try:
                src_manifest = json.loads(src_manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                src_manifest = {}
        entries = src_manifest.get("shots") or src_manifest.get("images") or []
        selected = set(shot_names) if shot_names else None
        copied = 0
        if isinstance(entries, list) and entries:
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                filename = str(entry.get("filename") or entry.get("file") or "")
                if not filename:
                    continue
                if selected is not None and filename not in selected and Path(filename).name not in selected:
                    continue
                src = batch / filename
                if not src.is_file():
                    continue
                shutil.copy2(src, dest / "vision" / Path(filename).name)
                manifest["shots"].append(
                    {
                        "filename": Path(filename).name,
                        "title": entry.get("title") or entry.get("name") or Path(filename).stem,
                        "notes": entry.get("notes") or entry.get("note") or "",
                    }
                )
                copied += 1
        if copied == 0:
            # Fall back: copy up to 12 PNGs
            for png in sorted(batch.glob("*.png"))[:12]:
                if selected is not None and png.name not in selected:
                    continue
                shutil.copy2(png, dest / "vision" / png.name)
                manifest["shots"].append({"filename": png.name, "title": png.stem, "notes": ""})

    (dest / "vision" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (dest / "output" / "README.md").write_text(
        "AI: write events/rois/presets here. Human: copy into the Idle Lab project and Refresh.\n",
        encoding="utf-8",
    )
    return dest
