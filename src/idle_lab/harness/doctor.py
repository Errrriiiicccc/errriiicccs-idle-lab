"""Resolve whether the active target window is findable for T3 live runs."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from idle_lab.harness.context import LabContext, TargetProfile, load_lab_context
from idle_lab.models import Rect
from idle_lab.presets import project_root
from idle_lab.settings_store import load_settings
from idle_lab.window_find import WindowCandidate


EnumWindowsFn = Callable[[], list[tuple[int, str, int, bool, bool]]]


@dataclass
class DoctorResult:
    ok: bool
    active_target: str
    target_label: str
    hwnd: int | None = None
    title: str | None = None
    rect: dict[str, int] | None = None
    match_mode: str | None = None
    last_anchor_title: str | None = None
    candidates_considered: int = 0
    hint: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _default_enum() -> list[tuple[int, str, int, bool, bool]]:
    from idle_lab import win32_api

    return win32_api.iter_top_level_windows()


def _rank(c: WindowCandidate) -> tuple[int, int]:
    if c.visible and not c.minimized:
        return (0, c.hwnd)
    if c.visible:
        return (1, c.hwnd)
    return (2, c.hwnd)


def _pick_best(matches: list[WindowCandidate]) -> WindowCandidate | None:
    if not matches:
        return None
    matches = sorted(matches, key=_rank)
    best_tier = _rank(matches[0])[0]
    top = [c for c in matches if _rank(c)[0] == best_tier]
    if len(top) != 1:
        return None
    return top[0]


def find_target_window(
    target: TargetProfile,
    *,
    last_anchor_title: str | None = None,
    our_pid: int | None = None,
    enum_windows: EnumWindowsFn | None = None,
) -> tuple[WindowCandidate | None, str | None, int]:
    """Return (candidate, match_mode, candidates_considered).

    Prefer exact last_anchor_title when ``prefer_last_anchor`` is set, then
    substring matches from the target profile.
    """

    pid = int(our_pid if our_pid is not None else os.getpid())
    enum_fn = enum_windows or _default_enum
    raw = enum_fn()
    candidates = [
        WindowCandidate(hwnd=h, title=t, pid=p, visible=v, minimized=m)
        for h, t, p, v, m in raw
        if h and p != pid and (t or "").strip()
    ]

    if target.prefer_last_anchor and last_anchor_title:
        needle = last_anchor_title.strip()
        exact = [c for c in candidates if c.title.strip() == needle]
        picked = _pick_best(exact)
        if picked is not None:
            return picked, "last_anchor_exact", len(candidates)

    for substring in target.anchor_title_substrings:
        needle = substring.casefold()
        hits = [c for c in candidates if needle in c.title.casefold()]
        picked = _pick_best(hits)
        if picked is not None:
            return picked, f"substring:{substring}", len(candidates)

    return None, None, len(candidates)


def run_doctor(
    *,
    root: Path | None = None,
    context: LabContext | None = None,
    enum_windows: EnumWindowsFn | None = None,
    get_rect: Callable[[int], Rect | None] | None = None,
) -> DoctorResult:
    project = root or project_root()
    ctx = context or load_lab_context(project)
    target = ctx.target

    settings, _ = load_settings(project / "settings.json")
    last_title = settings.last_anchor_title

    candidate, mode, considered = find_target_window(
        target,
        last_anchor_title=last_title,
        enum_windows=enum_windows,
    )

    if candidate is None:
        subs = ", ".join(repr(s) for s in target.anchor_title_substrings) or "(none)"
        hint = (
            f"Open {target.label} (window title matching {subs}"
            + (f" or last anchor {last_title!r}" if last_title else "")
            + "). Do not use Computer Use to hunt windows — fix the window, then re-run doctor."
        )
        return DoctorResult(
            ok=False,
            active_target=ctx.active_target,
            target_label=target.label,
            last_anchor_title=last_title,
            candidates_considered=considered,
            hint=hint,
            details={"substrings": list(target.anchor_title_substrings)},
        )

    rect_fn = get_rect
    if rect_fn is None:
        from idle_lab import win32_api

        rect_fn = win32_api.get_window_rect

    rect = rect_fn(candidate.hwnd)
    rect_dict = None
    if rect is not None:
        rect_dict = {
            "left": rect.left,
            "top": rect.top,
            "right": rect.right,
            "bottom": rect.bottom,
            "width": rect.width,
            "height": rect.height,
        }

    return DoctorResult(
        ok=True,
        active_target=ctx.active_target,
        target_label=target.label,
        hwnd=int(candidate.hwnd),
        title=candidate.title,
        rect=rect_dict,
        match_mode=mode,
        last_anchor_title=last_title,
        candidates_considered=considered,
        hint="Target window found; T3 live runs may proceed (will move the mouse).",
        details={"visible": candidate.visible, "minimized": candidate.minimized},
    )
