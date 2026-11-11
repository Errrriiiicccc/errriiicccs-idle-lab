"""Pure surface FSM + resume helpers for shape-first Phase 0."""

from __future__ import annotations

import unittest

from idle_lab.flight_deck.shell import EscAction, ShellPhase, resolve_escape
from idle_lab.shell.resume import resolve_resume_escape, resume_prompt
from idle_lab.shell.surfaces import (
    Surface,
    SurfaceKind,
    can_show_idle_lab,
    ensure_exclusive,
    hotkeys_allowed,
)
from idle_lab.shell.tabs import IDLE_LAB_TABS, DEFAULT_TAB, normalize_last_tab


class SurfaceFsmTests(unittest.TestCase):
    def test_running_blocks_idle_lab(self) -> None:
        self.assertTrue(can_show_idle_lab(anything_running=False))
        self.assertFalse(can_show_idle_lab(anything_running=True))

    def test_ensure_exclusive_forces_deck_when_running(self) -> None:
        surface = ensure_exclusive(
            want=SurfaceKind.IDLE_LAB,
            anything_running=True,
        )
        self.assertEqual(surface.kind, SurfaceKind.FLIGHT_DECK)
        self.assertFalse(surface.idle_lab_visible)
        self.assertTrue(surface.flight_deck_visible)

    def test_ensure_exclusive_honors_idle_lab_when_idle(self) -> None:
        surface = ensure_exclusive(
            want=SurfaceKind.IDLE_LAB,
            anything_running=False,
        )
        self.assertEqual(surface, Surface(SurfaceKind.IDLE_LAB))

    def test_hotkeys_only_on_flight_deck(self) -> None:
        self.assertFalse(hotkeys_allowed(surface=SurfaceKind.IDLE_LAB))
        self.assertTrue(hotkeys_allowed(surface=SurfaceKind.FLIGHT_DECK))
        self.assertTrue(hotkeys_allowed(surface="flight_deck", anything_running=True))


class LastTabTests(unittest.TestCase):
    def test_inventory(self) -> None:
        self.assertEqual(
            IDLE_LAB_TABS,
            ("Info", "Live Overlay Lab", "Molecule Lab", "Observation Lab"),
        )
        self.assertEqual(DEFAULT_TAB, "Info")

    def test_normalize_defaults_and_legacy(self) -> None:
        self.assertEqual(normalize_last_tab(None), "Info")
        self.assertEqual(normalize_last_tab("Live Overlay Lab"), "Live Overlay Lab")
        self.assertEqual(normalize_last_tab("LOL"), "Live Overlay Lab")
        self.assertEqual(normalize_last_tab("Bench"), "Molecule Lab")
        self.assertEqual(normalize_last_tab("Observe"), "Observation Lab")
        self.assertEqual(normalize_last_tab("Missions"), "Observation Lab")
        self.assertEqual(normalize_last_tab("Loops"), "Molecule Lab")
        self.assertEqual(normalize_last_tab("nope"), "Info")


class ResumeHandleTests(unittest.TestCase):
    def test_resume_prompt_names_choices(self) -> None:
        text = resume_prompt(activate_key="`")
        self.assertIn("continue", text.lower())
        self.assertIn("restart-wipe", text.lower())
        self.assertIn("Esc = Idle Lab", text)
        self.assertIn("[`]", text)

    def test_resolve_resume_escape(self) -> None:
        self.assertTrue(resolve_resume_escape(resume_handle=True, deck_inactive=True))
        self.assertFalse(resolve_resume_escape(resume_handle=False, deck_inactive=True))
        self.assertFalse(resolve_resume_escape(resume_handle=True, deck_inactive=False))

    def test_escape_opens_idle_lab_on_resume(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.INACTIVE,
                deck_active=False,
                resume_handle=True,
            ),
            EscAction.OPEN_IDLE_LAB,
        )
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.INACTIVE,
                deck_active=False,
                resume_handle=False,
            ),
            EscAction.NONE,
        )


if __name__ == "__main__":
    unittest.main()
