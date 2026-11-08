"""Compact observation digest for chats (avoid loading every PNG)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def build_observation_digest(folder: Path) -> dict[str, Any]:
    folder = Path(folder)
    header: dict[str, Any] = {}
    header_path = folder / "observation.json"
    if header_path.is_file():
        try:
            header = json.loads(header_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            header = {}
    events = _read_jsonl(folder / "timeline.jsonl")
    keyframes = []
    actions = []
    for row in events:
        kind = str(row.get("type") or "")
        if kind in {"keyframe", "mark"} or row.get("shot"):
            if row.get("shot"):
                keyframes.append(
                    {
                        "t_ms": row.get("t_ms"),
                        "type": kind,
                        "shot": row.get("shot"),
                        "role": row.get("role"),
                        "kind": row.get("kind"),
                        "nav": row.get("nav"),
                    }
                )
        if kind in {
            "pointer_up",
            "pointer_burst",
            "drag",
            "wheel",
            "action",
            "live_control_action",
            "manual_action",  # legacy Manual-mode timelines
        }:
            actions.append(
                {
                    "t_ms": row.get("t_ms"),
                    "type": kind,
                    "nx": row.get("nx") if "nx" in row else row.get("nx1"),
                    "ny": row.get("ny") if "ny" in row else row.get("ny1"),
                    "count": row.get("count", 1),
                    "nav": row.get("nav"),
                    "id": row.get("id"),
                    "action": row.get("action"),
                    "phase": row.get("phase"),
                    "detail": row.get("detail"),
                }
            )
    # Prefer a small suggested open set for chats.
    suggested = []
    for item in keyframes:
        role = str(item.get("role") or "")
        kind = str(item.get("kind") or "")
        if role in {"session-start", "mark"} or kind in {"drag", "wheel", "manual", "live_control"} or item.get("nav"):
            suggested.append(item.get("shot"))
    if not suggested and keyframes:
        suggested = [keyframes[0].get("shot"), keyframes[-1].get("shot")]
    suggested = [s for s in suggested if s][:8]
    return {
        "version": 1,
        "id": header.get("id") or folder.name,
        "title": header.get("title") or folder.name,
        "duration_ms": header.get("duration_ms"),
        "end_reason": header.get("end_reason"),
        "counts": header.get("counts") or {},
        "policy_mode": (header.get("policy") or {}).get("mode"),
        "action_count": len(actions),
        "actions": actions[:200],
        "keyframes": keyframes,
        "suggested_shots": suggested,
        "analysis_hint": (
            "Read observation.json + DIGEST.md/timeline actions first. "
            "Open only suggested_shots (or nav/drag/mark keyframes). Do not load every PNG."
        ),
    }


def write_observation_digest(folder: Path) -> Path:
    folder = Path(folder)
    digest = build_observation_digest(folder)
    json_path = folder / "digest.json"
    json_path.write_text(json.dumps(digest, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# Observation digest — {digest.get('title')}",
        "",
        digest["analysis_hint"],
        "",
        f"- Duration: {digest.get('duration_ms')} ms",
        f"- Mode: {digest.get('policy_mode')}",
        f"- Counts: `{json.dumps(digest.get('counts') or {})}`",
        f"- Actions summarized: {digest.get('action_count')}",
        "",
        "## Suggested shots (open these first)",
        "",
    ]
    for shot in digest.get("suggested_shots") or []:
        lines.append(f"- `{shot}`")
    if not digest.get("suggested_shots"):
        lines.append("- (none)")
    lines.extend(["", "## Action timeline (compact)", ""])
    for row in digest.get("actions") or []:
        loc = ""
        if row.get("nx") is not None and row.get("ny") is not None:
            loc = f" @ ({row['nx']:.2f},{row['ny']:.2f})"
        count = row.get("count") or 1
        extra = f" ×{count}" if count and count > 1 else ""
        nav = " [nav]" if row.get("nav") else ""
        lines.append(f"- t={row.get('t_ms')} {row.get('type')}{extra}{nav}{loc}")
    md_path = folder / "DIGEST.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path
