"""Shared overlay primitives — Live Overlay Lab + Atom Create."""

from __future__ import annotations

import unittest
from datetime import date

from idle_lab.screen_map.catalog import (
    GROUP_LAST_7,
    GROUP_THE_PAST,
    GROUP_TODAY,
    GROUP_YESTERDAY,
    catalog_group_for,
)
from idle_lab.shared_overlay import activity_style, nx_to_canvas, queue_index
from idle_lab.shell.atom_create import AtomCreatePhase, atom_create_prompt
from idle_lab.shell.console import SharedConsole
from idle_lab.shell.deck_mode import DeckMode, mode_abandons_menu, mode_display_name


class SharedOverlayTests(unittest.TestCase):
    def test_queue_and_style(self) -> None:
        self.assertEqual(queue_index(["A", "B"], "b"), 1)
        self.assertIsNone(queue_index(["A"], "Z"))
        outline, fill = activity_style(current=True)
        self.assertTrue(outline.startswith("#"))
        self.assertTrue(fill.startswith("#"))
        self.assertEqual(nx_to_canvas(0.5, 0.5, width=101, height=101), (50, 50))

    def test_atom_create_no_fake_save(self) -> None:
        text = atom_create_prompt(phase=AtomCreatePhase.CREATE)
        self.assertIn("accordion", text.lower())
        self.assertIn("no silent save", text.lower())
        idle = atom_create_prompt(phase=AtomCreatePhase.IDLE)
        self.assertIn("no silent save", idle.lower())

    def test_atom_create_mode_abandons_menu(self) -> None:
        self.assertTrue(mode_abandons_menu(DeckMode.ATOM_CREATE))
        self.assertEqual(mode_display_name(DeckMode.ATOM_CREATE), "Atom Create")

    def test_atom_create_keymap_is_accordion(self) -> None:
        from idle_lab.shell.atom_create import build_atom_create_keymap

        keymap = build_atom_create_keymap(step_count=2)
        keys = {n.key.upper() for n in keymap.roots}
        self.assertEqual(keys, {"B", "T", "S", "U", "K", "E"})
        buys = next(n for n in keymap.roots if n.key.upper() == "B")
        self.assertFalse(buys.is_leaf)
        self.assertIn("2 step", buys.label)
        self.assertEqual(buys.children[0].action["type"], "atom_add_lco")

    def test_shared_console_fanout(self) -> None:
        console = SharedConsole(maxlen=10)
        seen: list[str] = []
        console.subscribe(lambda line: seen.append(line.message))
        console.append("hello", "ok")
        self.assertEqual(seen, ["hello"])
        self.assertEqual(console.lines()[0].level, "ok")

    def test_catalog_groups(self) -> None:
        today = date(2026, 11, 10)
        self.assertEqual(catalog_group_for("2026-11-10T12:00:00", today=today), GROUP_TODAY)
        self.assertEqual(catalog_group_for("2026-11-09", today=today), GROUP_YESTERDAY)
        self.assertEqual(catalog_group_for("2026-11-05", today=today), GROUP_LAST_7)
        self.assertEqual(catalog_group_for("2026-10-01", today=today), GROUP_THE_PAST)


if __name__ == "__main__":
    unittest.main()
