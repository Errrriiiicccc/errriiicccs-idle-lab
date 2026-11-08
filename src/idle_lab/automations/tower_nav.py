"""Tower upgrade-panel status helpers for Automations (observe before acting)."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from typing import Callable

from PIL import Image

from idle_lab.ai_batch.panel_detect import PanelState, detect_upgrade_panel
from idle_lab.ai_batch.scroll_metrics import crop_normalized, mean_abs_diff
from idle_lab.automations.capture import CaptureError, grab_anchor
from idle_lab.automations.ocr import run_ocr
from idle_lab.click_foreground import foreground_drag
from idle_lab.humanize import HumanizeProfile, human_click
from idle_lab.models import Rect, normalized_to_screen
from idle_lab import win32_api

TAB_CLICK = {
    "attack": (0.20, 0.955),
    "defense": (0.40, 0.955),
    "utility": (0.60, 0.955),
}

# First-row buy aim (Damage on Attack / Health on Defense) when list is at top.
BUY_CLICK = {
    "damage": (0.38, 0.735),
    "health": (0.38, 0.735),
}

# Upgrade list body — used for scroll-unchanged compares (playbook).
LIST_COMPARE_ROI = {"nx": 0.04, "ny": 0.55, "nw": 0.92, "nh": 0.36}

# First upgrade card title/value band (Damage / Health when at top).
FIRST_CARD_ROI = {"nx": 0.08, "ny": 0.67, "nw": 0.55, "nh": 0.08}

# Drag start inside the list.
LIST_DRAG = {"nx": 0.45, "ny": 0.70}


@dataclass(frozen=True)
class ListTopCheck:
    at_top: bool
    observation: str
    reason: str


def panel_status_vars(state: PanelState) -> dict[str, object]:
    return {
        "panel_open": "yes" if state.panel_open else "no",
        "upgrade_tab": state.tab or "none",
        "panel_reason": state.reason,
        "panel_rgb": ",".join(f"{c:.0f}" for c in state.mean_rgb),
    }


def check_list_top(image: Image.Image, look_for: str, *, roi: dict[str, float] | None = None) -> ListTopCheck:
    """OCR the first-card band; at_top if look_for appears as a word."""

    box = roi or FIRST_CARD_ROI
    crop = crop_normalized(image, **box)
    observation = run_ocr(crop)
    needle = (look_for or "").strip()
    if not needle:
        return ListTopCheck(at_top=False, observation=observation, reason="no look_for keyword")
    pattern = r"(?<![A-Za-z0-9])" + re.escape(needle) + r"(?![A-Za-z0-9])"
    if re.search(pattern, observation or "", flags=re.IGNORECASE):
        return ListTopCheck(
            at_top=True,
            observation=observation,
            reason=f"first card OCR contains {needle!r}",
        )
    return ListTopCheck(
        at_top=False,
        observation=observation,
        reason=f"first card OCR missing {needle!r} (saw {observation!r})",
    )


def click_normalized(
    *,
    hwnd: int,
    rect: Rect,
    nx: float,
    ny: float,
    hold_ms: int = 70,
    restore_cursor: bool = True,
    profile: HumanizeProfile | None = None,
    focus: bool = True,
    stop: threading.Event | None = None,
) -> None:
    if stop is not None and stop.is_set():
        return
    if focus and hwnd:
        win32_api.focus_window(hwnd)
        time.sleep(0.05)
    x, y = normalized_to_screen(rect, nx, ny)
    human_click(
        x,
        y,
        hold_ms,
        method="foreground",
        hwnd=hwnd,
        restore_cursor=restore_cursor,
        profile=profile or HumanizeProfile.from_level("medium"),
        rect=rect,
        stop=stop,
    )


def drag_list(
    *,
    hwnd: int,
    rect: Rect,
    direction: str = "up",
    nx: float = LIST_DRAG["nx"],
    ny: float = LIST_DRAG["ny"],
    drag_fraction: float = 0.10,
    hold_end_ms: int = 450,
    drag_steps: int = 12,
    step_ms: int = 30,
    restore_cursor: bool = True,
    focus: bool = True,
    stop: threading.Event | None = None,
) -> None:
    """One controlled partial drag (playbook: ~one tile row, hold before release)."""

    if stop is not None and stop.is_set():
        return
    if focus and hwnd:
        win32_api.focus_window(hwnd)
        time.sleep(0.05)
    # Allow up to ~half the list height for single-gesture page scrolls.
    fraction = max(0.03, min(0.50, abs(float(drag_fraction))))
    # Finger opposite list direction: up-list → drag down.
    delta = fraction if direction.lower() in ("up", "left") else -fraction
    start_ny = max(0.05, min(0.95, float(ny)))
    end_ny = max(0.05, min(0.95, start_ny + delta))
    start_x, start_y = normalized_to_screen(rect, nx, start_ny)
    end_x, end_y = normalized_to_screen(rect, nx, end_ny)
    foreground_drag(
        start_x,
        start_y,
        end_x,
        end_y,
        restore_cursor=restore_cursor,
        steps=max(2, abs(int(drag_steps))),
        step_ms=max(1, abs(int(step_ms))),
        hold_end_ms=max(0, abs(int(hold_end_ms))),
        stop=stop,
    )


def fling_list(
    *,
    hwnd: int,
    rect: Rect,
    direction: str = "up",
    nx: float = LIST_DRAG["nx"],
    ny: float = LIST_DRAG["ny"],
    drag_fraction: float = 0.42,
    drag_steps: int = 5,
    step_ms: int = 4,
    restore_cursor: bool = True,
    focus: bool = True,
    stop: threading.Event | None = None,
) -> None:
    """Fast swipe with immediate release so list momentum carries to the end."""

    drag_list(
        hwnd=hwnd,
        rect=rect,
        direction=direction,
        nx=nx,
        ny=ny,
        drag_fraction=max(0.25, min(0.50, abs(float(drag_fraction)))),
        hold_end_ms=0,
        drag_steps=max(3, abs(int(drag_steps))),
        step_ms=max(1, abs(int(step_ms))),
        restore_cursor=restore_cursor,
        focus=focus,
        stop=stop,
    )


def grab_list_roi(rect: Rect, *, roi: dict[str, float] | None = None) -> tuple[Image.Image, Image.Image]:
    image = grab_anchor(rect)
    box = roi or LIST_COMPARE_ROI
    return image, crop_normalized(image, **box)


def seek_list_top(
    *,
    hwnd: int,
    rect: Rect,
    look_for: str = "",
    max_steps: int = 12,
    settle_ms: int = 800,
    settle_confirm_ms: int = 400,
    unchanged_threshold: float = 0.015,
    drag_fraction: float = 0.10,
    hold_end_ms: int = 450,
    restore_cursor: bool = True,
    stop: threading.Event | None = None,
    log: Callable[[str, str], None] | None = None,
    save_status: Callable[[Image.Image, str], None] | None = None,
) -> dict[str, object]:
    """Scroll the upgrade list up until the top row is visible or the list stops moving.

    Prefers OCR ``look_for`` (Health / Damage). Falls back to unchanged ROI compare.
    """

    def _log(message: str, level: str = "info") -> None:
        if log:
            log(message, level)

    try:
        image = grab_anchor(rect)
    except CaptureError:
        raise

    if look_for:
        check = check_list_top(image, look_for)
        _log(f"list top check: {check.reason}", "info")
        if save_status:
            save_status(image, "list-top-00-before")
        if check.at_top:
            return {
                "scrolled": False,
                "steps": 0,
                "at_top": True,
                "stop_reason": "ocr_match",
                "observation": check.observation,
            }

    previous = crop_normalized(image, **LIST_COMPARE_ROI)
    applied = 0
    stop_reason = "max_steps"
    last_observation = ""

    for index in range(1, max(1, max_steps) + 1):
        if stop is not None and stop.is_set():
            stop_reason = "aborted"
            break
        drag_list(
            hwnd=hwnd,
            rect=rect,
            direction="up",
            drag_fraction=drag_fraction,
            hold_end_ms=hold_end_ms,
            restore_cursor=restore_cursor,
            stop=stop,
        )
        applied += 1
        if settle_ms:
            time.sleep(settle_ms / 1000.0)
        after_image, after_roi = grab_list_roi(rect)
        if settle_confirm_ms:
            time.sleep(settle_confirm_ms / 1000.0)
            confirm_image, confirm_roi = grab_list_roi(rect)
            residual = mean_abs_diff(after_roi, confirm_roi)
            if residual >= unchanged_threshold:
                time.sleep(settle_ms / 1000.0 if settle_ms else settle_confirm_ms / 1000.0)
                after_image, after_roi = grab_list_roi(rect)
            else:
                after_image = confirm_image
                after_roi = confirm_roi

        delta = mean_abs_diff(previous, after_roi)
        if save_status:
            save_status(after_image, f"list-top-{index:02d}-status")

        if look_for:
            check = check_list_top(after_image, look_for)
            last_observation = check.observation
            _log(
                f"seek up #{index}: Δ={delta:.4f}; {check.reason}",
                "info",
            )
            if check.at_top:
                stop_reason = "ocr_match"
                previous = after_roi
                return {
                    "scrolled": True,
                    "steps": applied,
                    "at_top": True,
                    "stop_reason": stop_reason,
                    "observation": last_observation,
                    "last_delta": round(delta, 5),
                }
        else:
            _log(f"seek up #{index}: Δ={delta:.4f}", "info")

        if delta < unchanged_threshold:
            stop_reason = "unchanged"
            _log(f"list edge (top): unchanged Δ={delta:.4f}", "ok")
            return {
                "scrolled": applied > 0,
                "steps": applied,
                "at_top": True,
                "stop_reason": stop_reason,
                "observation": last_observation,
                "last_delta": round(delta, 5),
            }
        previous = after_roi

    _log(f"seek_list_top stopped ({stop_reason}) after {applied} drag(s)", "warn")
    return {
        "scrolled": applied > 0,
        "steps": applied,
        "at_top": stop_reason in {"unchanged", "ocr_match"},
        "stop_reason": stop_reason,
        "observation": last_observation,
    }


def observe_panel(image: Image.Image) -> PanelState:
    return detect_upgrade_panel(image)
