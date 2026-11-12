"""Info tab nested outline — verbose onboarding (shape-first)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InfoLink:
    label: str
    tab: str  # Idle Lab tab name


@dataclass(frozen=True)
class InfoSection:
    title: str
    body: str
    checklist: tuple[str, ...] = ()
    links: tuple[InfoLink, ...] = ()
    children: tuple["InfoSection", ...] = field(default_factory=tuple)


# "How it talks" lives in feel_tray.py as interactive specimens — not prose here.

INFO_OUTLINE: tuple[InfoSection, ...] = (
    InfoSection(
        title="What Idle Lab is",
        body=(
            "Idle Lab is a human-translation workbench: you show a screen, say what you "
            "see and want, and the system turns that into repeatable automations. "
            "Files are the language. AI authors; Idle Lab executes and evidences. "
            "The Tower is the proving ground until the workbench is much cleaner."
        ),
        checklist=(
            "Prefer structured exports / title hooks before OCR guessing",
            "Fail loudly — never green-fake success",
            "Attended: Anchor, Refresh, Restart, Deactivate stay obvious",
        ),
    ),
    InfoSection(
        title="Two surfaces",
        body=(
            "Idle Lab is the mouse-dense home (no keyboard hotkeys while open). "
            "Flight Deck is the hotkey companion. Never show both at once. "
            "Factory boot opens Idle Lab on Info; Settings can prefer Deck boot. "
            "Anything running → Idle Lab closes; Deck only."
        ),
        checklist=(
            "Idle Lab open → buttons only",
            "Deck starts deactivated — only ` until Activate",
            "Deactivate (`) = Stop all + resume handle",
        ),
    ),
    InfoSection(
        title="Nomenclature",
        body=(
            "Labs: Info, Live Overlay Lab, Molecule Lab, Observation Lab. "
            "Atoms and molecules are file-backed procedures. Anchor locks the target window. "
            "Current State (later) is queryable layered screen memory. "
            "Legacy words Bench / Loops / Missions / LCO map into these Labs."
        ),
    ),
    InfoSection(
        title="Chrome",
        body=(
            "Anchor the target. Restart reloads code. Settings holds boot preference "
            "(and Activate-key remap). Live status lives in this header strip — not inside Info. "
            "Deactivate on Idle Lab chrome matches Deck Deactivate: stop every runner."
        ),
    ),
    InfoSection(
        title="Labs",
        body="Each Lab is a focused module. Use checklists below; links jump to the tab.",
        children=(
            InfoSection(
                title="Live Overlay Lab",
                body=(
                    "Interactive target map + live object-map hands. "
                    "Shares overlay primitives with Atom Create. "
                    "Live start hides Idle Lab and uses Deck; Esc returns to the entry surface."
                ),
                checklist=(
                    "Anchor before starting Live Overlay Lab live",
                    "Hold D describes overlay hotkeys",
                    "Esc exits live mode (not Deactivate)",
                ),
                links=(InfoLink("Open Live Overlay Lab tab", "Live Overlay Lab"),),
            ),
            InfoSection(
                title="Molecule Lab",
                body=(
                    "Atom create/edit + molecule compose. Autoclicker energy lives under Atom. "
                    "Deck M opens a floating Molecule Lab. Start-all-enabled is cut."
                ),
                checklist=(
                    "Build simple atoms first, then compose",
                    "Refresh after editing atom/molecule JSON on disk",
                    "Trial polish is parked — skeleton honesty over fake polish",
                ),
                links=(InfoLink("Open Molecule Lab tab", "Molecule Lab"),),
            ),
            InfoSection(
                title="Observation Lab",
                body=(
                    "User capture/review + AI mission panes in one Lab. "
                    "Mark and rename-on-stop are cut. Stop capture with Deactivate (`)."
                ),
                checklist=(
                    "Review catalog will group Today / Yesterday / Last 7 / The Past",
                    "Missions live as AI mission panes here — not a separate top-level tab",
                    "Delete observations deliberately; do not auto-archive",
                ),
                links=(InfoLink("Open Observation Lab tab", "Observation Lab"),),
            ),
        ),
    ),
    InfoSection(
        title="Running / Deactivate / resume",
        body=(
            "When something runs, Idle Lab withdraws and Deck owns the surface. "
            "` Deactivate stops everything and shows a resume handle: "
            "Activate again to continue, restart-wipe (later), or Esc back to Idle Lab."
        ),
        checklist=(
            "One stop model — Deactivate = Stop all",
            "No separate Pause beside Deactivate",
            "Global Refresh reloads disk data; Restart reloads code",
        ),
    ),
    InfoSection(
        title="Sense ladder (deeper)",
        body=(
            "Prefer trustworthy data in order: structured source → title-native hooks → "
            "pixels / OCR / our atoms. Bad data must abstain, not invent quantities."
        ),
        children=(
            InfoSection(
                title="File locations (sketch)",
                body=(
                    "Atoms/events and molecules/collections live under automations/. "
                    "Flight Deck letter map: automations/flight_deck.json. "
                    "Observations and AI batches under screen-maps/ and ai-batches/. "
                    "Package/disk renames lag operator labels on purpose."
                ),
            ),
        ),
    ),
)
