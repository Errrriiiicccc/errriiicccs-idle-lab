"""Nav path helpers for Molecule Lab leaves (inner Tabview removed)."""

from __future__ import annotations

import unittest

from idle_lab.shell.nav import join_path, normalize_nav_path, path_leaf, path_root


class NavPathTests(unittest.TestCase):
    def test_molecule_defaults(self) -> None:
        self.assertEqual(normalize_nav_path("Molecule Lab"), "Molecule Lab/Atom")
        self.assertEqual(join_path("Molecule Lab", "Trial"), "Molecule Lab/Trial")
        self.assertEqual(path_root("Molecule Lab/Molecule"), "Molecule Lab")
        self.assertEqual(path_leaf("Molecule Lab/Molecule"), "Molecule")

    def test_observation_legacy(self) -> None:
        self.assertEqual(normalize_nav_path("Observe"), "Observation Lab/User")
        self.assertEqual(normalize_nav_path("Missions"), "Observation Lab/AI mission")


if __name__ == "__main__":
    unittest.main()
