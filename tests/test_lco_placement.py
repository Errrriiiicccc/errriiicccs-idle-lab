"""Molecule LCO placement persistence + hotkey conflict remaps."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.composer.lco_placement import (
    MoleculeLcoPlacement,
    enabled_placements,
    next_free_key,
    resolve_hotkey_conflicts,
    save_placement,
    set_enabled,
)


class LcoPlacementTests(unittest.TestCase):
    def test_conflict_remaps_second_molecule(self) -> None:
        places = [
            MoleculeLcoPlacement("a", title="A", enabled=True, hotkey="Z"),
            MoleculeLcoPlacement("b", title="B", enabled=True, hotkey="Z"),
        ]
        remaps = resolve_hotkey_conflicts(places, reserved={"Q", "W"})
        self.assertEqual(places[0].hotkey, "Z")
        self.assertNotEqual(places[1].hotkey, "Z")
        self.assertTrue(remaps)
        self.assertEqual(remaps[0][0], "b")

    def test_reserved_key_forced_off_key(self) -> None:
        places = [MoleculeLcoPlacement("a", enabled=True, hotkey="Q")]
        remaps = resolve_hotkey_conflicts(places, reserved={"Q"})
        self.assertNotEqual(places[0].hotkey, "Q")
        self.assertTrue(remaps)

    def test_next_free_skips_taken(self) -> None:
        free = next_free_key({"A", "B"}, reserved={"C"})
        self.assertEqual(free, "D")

    def test_persist_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "composer").mkdir(parents=True)
            (root / "collections").mkdir()
            place = set_enabled(root, "mol_demo", enabled=True, title="Demo", reserved={"Q"})
            self.assertTrue(place.enabled)
            self.assertIsNotNone(place.hotkey)
            place.nx = 0.22
            place.ny = 0.55
            save_placement(root, place)
            draft = json.loads((root / "composer" / "drafts" / "mol_demo.json").read_text(encoding="utf-8"))
            self.assertTrue(draft["lco"]["enabled"])
            self.assertAlmostEqual(draft["lco"]["nx"], 0.22)
            enabled = enabled_placements(root, reserved={"Q"})
            self.assertEqual(len(enabled), 1)
            self.assertAlmostEqual(enabled[0].nx, 0.22)


if __name__ == "__main__":
    unittest.main()
