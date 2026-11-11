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
    CANCEL_LCO_REBIND = "cancel_lco_rebind"
    CANCEL_REMAP = "cancel_remap"
    CANCEL_CLOSE = "cancel_close"
    CANCEL_MOLECULE_LAB_CLOSE = "cancel_molecule_lab_close"
    ENTER_MOLECULE_LAB_CLOSE = "enter_molecule_lab_close"
    CLOSE_MOLECULE_LAB = "close_molecule_lab"
    CLOSE_SECTION = "close_section"
    COLLAPSE_MENU = "collapse_menu"
    ENTER_CLOSE_CONFIRM = "enter_close_confirm"
    OPEN_IDLE_LAB = "open_idle_lab"
    NONE = "none"


def resolve_escape(
    *,
    phase: ShellPhase | str,
    live_control_active: bool = False,
    live_control_rebinding: bool = False,
    molecule_lab_active: bool = False,
    molecule_lab_close_confirm: bool = False,
    remap_active: bool = False,
    deck_active: bool = False,
    deck_expanded: bool = False,
    open_menu: bool = False,
    resume_handle: bool = False,
) -> EscAction:
    """Map Esc. Deactivate is never Esc — that is the Activate key only.

    Inactive: Esc ignored unless post-Deactivate resume handle → Idle Lab.
    Active: peel menu, then close-confirm (not deactivate).
    Close confirm: Esc cancels.
    """

    # LCO owns Esc while armed — even if Molecule Lab is also open underneath.
    if live_control_active and live_control_rebinding:
        return EscAction.CANCEL_LCO_REBIND
    if live_control_active:
        return EscAction.EXIT_LIVE_CONTROL
    if molecule_lab_close_confirm:
        return EscAction.CANCEL_MOLECULE_LAB_CLOSE
    if molecule_lab_active:
        return EscAction.ENTER_MOLECULE_LAB_CLOSE
    if remap_active:
        return EscAction.CANCEL_REMAP

    phase_norm = phase if isinstance(phase, ShellPhase) else ShellPhase(str(phase))
    if phase_norm is ShellPhase.CLOSE_CONFIRM:
        return EscAction.CANCEL_CLOSE
    if phase_norm is ShellPhase.INACTIVE or not deck_active:
        if resume_handle:
            return EscAction.OPEN_IDLE_LAB
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


def live_control_legend_hint(*, show_descriptors: bool = False, paused: bool = False) -> str:
    """Bold flight-deck headline while LCO is on — hold D for descriptors."""

    _ = paused
    if show_descriptors:
        return "HOLDING D = DESCRIBE"
    return "HOLD D = DESCRIBE"


def live_control_active_prompt(*, paused: bool = False, activate_key: str = "`") -> str:
    """Flight-deck body while Live Control Overlay owns the keys."""

    _ = paused
    key = (activate_key or "`").strip() or "`"
    return (
        "LCO is active\n"
        "Clicks show hotkeys · scroll / stat / refresh show icons\n"
        "Hold D to describe · drag Lab molecules · click mark to rebind\n"
        f"{key} = deactivate (stops all + idle deck) · Esc = exit LCO only"
    )


def molecule_lab_active_prompt(*, close_confirm: bool = False) -> str:
    """Flight-deck body while Molecule Lab owns Esc (deck hotkeys paused)."""

    if close_confirm:
        return "Close Molecule Lab?\nEnter = yes · Esc = stay"
    return (
        "Molecule Lab is open\n"
        "Deck hotkeys paused — type in Lab text boxes\n"
        "Esc = close · Enter confirms close"
    )


def molecule_lab_legend_hint(*, close_confirm: bool = False) -> str:
    if close_confirm:
        return "ENTER = CLOSE LAB"
    return "ESC = CLOSE LAB"


def active_unanchored_prompt(
    *,
    last_title: str | None,
    candidate_found: bool,
    lab_visible: bool,
) -> str:
    title = (last_title or "").strip()
    lab = "" if lab_visible else " · I = open Lab"
    extras = f"{lab} · R = restart (re-anchors)"
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
