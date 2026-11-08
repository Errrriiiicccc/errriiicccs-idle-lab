"""Pure Esc / activate helpers for deck-first launch."""

from __future__ import annotations

from enum import Enum


class ShellPhase(str, Enum):
    """UI chrome phase (what the deck is showing)."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    CLOSE_CONFIRM = "close_confirm"


class EscAction(str, Enum):
    EXIT_LIVE_CONTROL = "exit_live_control"
    CANCEL_REMAP = "cancel_remap"
    CANCEL_CLOSE = "cancel_close"
    CLOSE_SECTION = "close_section"
    COLLAPSE_MENU = "collapse_menu"
    ENTER_CLOSE_CONFIRM = "enter_close_confirm"
    NONE = "none"


def resolve_escape(
    *,
    phase: ShellPhase | str,
    live_control_active: bool = False,
    remap_active: bool = False,
    deck_active: bool = False,
    deck_expanded: bool = False,
    open_menu: bool = False,
) -> EscAction:
    """Map Esc. Deactivate is never Esc — that is the Activate key only.

    Inactive: Esc ignored.
    Active: peel menu, then close-confirm (not deactivate).
    Close confirm: Esc cancels.
    """

    if live_control_active:
        return EscAction.EXIT_LIVE_CONTROL
    if remap_active:
        return EscAction.CANCEL_REMAP

    phase_norm = phase if isinstance(phase, ShellPhase) else ShellPhase(str(phase))
    if phase_norm is ShellPhase.CLOSE_CONFIRM:
        return EscAction.CANCEL_CLOSE
    if phase_norm is ShellPhase.INACTIVE or not deck_active:
        return EscAction.NONE

    # Anchored active keeps the hotkey accordion open as the main surface — that is
    # not a peel layer. Only an open letter-section peels; otherwise Esc = close.
    if open_menu:
        return EscAction.CLOSE_SECTION
    return EscAction.ENTER_CLOSE_CONFIRM


def close_confirm_prompt(*, lab_visible: bool) -> str:
    if lab_visible:
        return "Close flight deck? Enter = yes · Esc = stay"
    return "Quit Idle Lab? Enter = quit · Esc = stay"


def inactive_prompt(*, activate_key: str) -> str:
    return f"Activate Flight Deck [{activate_key}]"


def live_control_legend_hint(*, show_hotkeys: bool = False, paused: bool = False) -> str:
    """Bold flight-deck headline while LCO is on — D flips icon ↔ hotkey marks."""

    if paused:
        return "` = RESUME LCO"
    if show_hotkeys:
        return "D = SWITCH HOTKEYS BACK TO ICONS"
    return "D = SWITCH ICONS TO HOTKEYS"


def live_control_active_prompt(*, paused: bool = False) -> str:
    """Flight-deck body while Live Control Overlay owns the keys."""

    if paused:
        return (
            "LCO paused — marks gray / inert · typing passes through\n"
            "` resumes · Esc exits LCO"
        )
    return (
        "LCO is active\n"
        "Clicks show hotkeys · scroll / stat / refresh show icons\n"
        "` pauses · Esc exits LCO"
    )


def active_unanchored_prompt(
    *,
    last_title: str | None,
    candidate_found: bool,
    lab_visible: bool,
) -> str:
    title = (last_title or "").strip()
    lab = "" if lab_visible else " · I = open Lab"
    extras = f"{lab} · R = restart"
    if title and candidate_found:
        short = title if len(title) <= 32 else title[:29] + "…"
        return f'Re-anchor “{short}”? Enter = yes · A = new{extras} · Esc = close'
    if title:
        short = title if len(title) <= 28 else title[:25] + "…"
        return f'“{short}” not found. A = set anchor{extras} · Esc = close'
    return f"A = set anchor{extras} · Esc = close"


def boot_prompt(*, last_title: str | None, candidate_found: bool) -> str:
    """Compatibility alias for the active-unanchored prompt (Lab hidden)."""

    return active_unanchored_prompt(
        last_title=last_title,
        candidate_found=candidate_found,
        lab_visible=False,
    )
