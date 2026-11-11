"""Deck mode abandon + Settings boot preference helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from idle_lab.flight_deck.shell import EscAction, ShellPhase, resolve_escape
from idle_lab.models import Settings
from idle_lab.settings_store import load_settings, save_settings
from idle_lab.shell.deck_mode import (
    DeckMode,
    mode_abandons_menu,
    mode_display_name,
    mode_legend,
    mode_prompt,
)
from idle_lab.shell.info_content import INFO_OUTLINE
from idle_lab.shell.settings_panel import BOOT_FLIGHT_DECK, BOOT_IDLE_LAB, normalize_boot_surface


class DeckModeTests(unittest.TestCase):
    def test_menu_does_not_abandon(self) -> None:
        self.assertFalse(mode_abandons_menu(DeckMode.MENU))
        self.assertTrue(mode_abandons_menu(DeckMode.LOL))
        self.assertTrue(mode_abandons_menu(DeckMode.MOLECULE_LAB))
        self.assertTrue(mode_abandons_menu(DeckMode.OBSERVATION_LAB))
        self.assertTrue(mode_abandons_menu(DeckMode.SETTINGS))

    def test_mode_prompt_is_honest_stub(self) -> None:
        text = mode_prompt(DeckMode.LOL, activate_key="`")
        self.assertIn("not wired", text.lower())
        self.assertIn("Esc", text)
        self.assertIn("`", text)
        self.assertIn("Deactivate", text)

    def test_escape_exits_deck_mode(self) -> None:
        self.assertEqual(
            resolve_escape(
                phase=ShellPhase.ACTIVE,
                deck_active=True,
                deck_mode_active=True,
            ),
            EscAction.EXIT_DECK_MODE,
        )
        self.assertEqual(mode_legend(DeckMode.SETTINGS), "ESC = CLOSE SETTINGS")
        self.assertEqual(mode_display_name(DeckMode.LOL), "Live Overlay Lab")
        self.assertEqual(mode_legend(DeckMode.LOL), "ESC = EXIT LIVE OVERLAY LAB")


class BootSurfaceTests(unittest.TestCase):
    def test_normalize(self) -> None:
        self.assertEqual(normalize_boot_surface(None), BOOT_IDLE_LAB)
        self.assertEqual(normalize_boot_surface("flight_deck"), BOOT_FLIGHT_DECK)
        self.assertEqual(normalize_boot_surface("Deck"), BOOT_FLIGHT_DECK)
        self.assertEqual(normalize_boot_surface("idle_lab"), BOOT_IDLE_LAB)

    def test_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            settings = Settings(boot_surface=BOOT_FLIGHT_DECK, last_tab="Live Overlay Lab")
            save_settings(path, settings)
            loaded, err = load_settings(path)
            self.assertIsNone(err)
            self.assertEqual(loaded.boot_surface, BOOT_FLIGHT_DECK)
            self.assertEqual(loaded.last_tab, "Live Overlay Lab")


class InfoOutlineTests(unittest.TestCase):
    def test_outline_covers_labs_and_links(self) -> None:
        titles = {section.title for section in INFO_OUTLINE}
        self.assertIn("What Idle Lab is", titles)
        self.assertIn("Two surfaces", titles)
        self.assertIn("Labs", titles)
        labs = next(s for s in INFO_OUTLINE if s.title == "Labs")
        child_titles = {c.title for c in labs.children}
        self.assertIn("Live Overlay Lab", child_titles)
        self.assertNotIn("LOL", child_titles)
        self.assertIn("Molecule Lab", child_titles)
        self.assertIn("Observation Lab", child_titles)
        linked_tabs = {link.tab for child in labs.children for link in child.links}
        self.assertEqual(
            linked_tabs,
            {"Live Overlay Lab", "Molecule Lab", "Observation Lab"},
        )


if __name__ == "__main__":
    unittest.main()
