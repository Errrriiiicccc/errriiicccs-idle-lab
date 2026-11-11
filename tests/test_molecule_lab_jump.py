"""Molecule Lab sub-tab jump helpers."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from idle_lab.shell.tabs.molecule_lab import find_ml_root, select_ml_subtab


class _FakeTabs:
    def __init__(self) -> None:
        self.current = "Atom"

    def set(self, name: str) -> None:
        self.current = name


class MoleculeLabJumpTests(unittest.TestCase):
    def test_find_root_walks_ancestors(self) -> None:
        root = SimpleNamespace(_ml_tabs=_FakeTabs())
        mid = SimpleNamespace(master=root)
        leaf = SimpleNamespace(master=mid)
        self.assertIs(find_ml_root(leaf), root)
        self.assertIsNone(find_ml_root(SimpleNamespace(master=None)))

    def test_select_from_descendant(self) -> None:
        tabs = _FakeTabs()
        root = SimpleNamespace(_ml_tabs=tabs)
        leaf = SimpleNamespace(master=root)
        self.assertTrue(select_ml_subtab(leaf, "Molecule"))
        self.assertEqual(tabs.current, "Molecule")


if __name__ == "__main__":
    unittest.main()
