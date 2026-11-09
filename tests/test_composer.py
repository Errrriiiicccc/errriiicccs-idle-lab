"""Molecule composer — palette gating + expand/export."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.composer.catalog import load_capability_catalog
from idle_lab.composer.expand import expand_and_write, load_library, preview_expansion
from idle_lab.composer.model import (
    ComposerContext,
    ComposerDraft,
    DraftStep,
    SeekGuards,
    build_palette,
)
from idle_lab.presets import project_root


class ComposerPaletteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_capability_catalog(project_root())

    def test_catalog_has_attack_upgrades(self) -> None:
        self.assertIn("attack", self.catalog.tabs)
        attack = self.catalog.tabs["attack"]
        labels = [e.label for e in attack.catalog]
        self.assertIn("Damage", labels)
        self.assertTrue(any("Multishot" in label or "Multi" in label for label in labels))

    def test_empty_context_only_tabs(self) -> None:
        items = build_palette(context=ComposerContext(), tabs=self.catalog.tabs, library=[])
        self.assertTrue(items)
        self.assertTrue(all(item.kind == "ensure_tab" for item in items))
        self.assertFalse(any(item.kind == "seek_and_buy" for item in items))

    def test_attack_context_shows_buys_not_other_tabs(self) -> None:
        ctx = ComposerContext()
        ctx.enter_tab("attack")
        items = build_palette(context=ctx, tabs=self.catalog.tabs, library=[])
        kinds = {item.kind for item in items}
        self.assertIn("seek_and_buy", kinds)
        labels = [item.label for item in items if item.kind == "seek_and_buy"]
        self.assertIn("Damage", labels)
        self.assertNotIn("Health", labels)

    def test_library_molecule_scoped_to_tab(self) -> None:
        ctx = ComposerContext()
        ctx.enter_tab("attack")
        library = [
            {"id": "mol_atk_pack", "title": "Atk pack", "requires_tab": "attack"},
            {"id": "mol_def_pack", "title": "Def pack", "requires_tab": "defense"},
        ]
        items = build_palette(context=ctx, tabs=self.catalog.tabs, library=library)
        mol_ids = [item.molecule_id for item in items if item.kind == "molecule_ref"]
        self.assertIn("mol_atk_pack", mol_ids)
        self.assertNotIn("mol_def_pack", mol_ids)

    def test_multishot_guards_include_rapid_fire(self) -> None:
        attack = self.catalog.tabs["attack"]
        entry = next(e for e in attack.catalog if "Multishot Chance" in e.label or "Multi" in e.label)
        guards = attack.guards_for(entry)
        joined = " ".join(guards.too_far_down).lower()
        self.assertTrue("rapid" in joined or "bounce" in joined or "multishot" in joined)


class ComposerExpandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_capability_catalog(project_root())

    def test_preview_and_export(self) -> None:
        attack = self.catalog.tabs["attack"]
        damage = next(e for e in attack.catalog if e.label == "Damage")
        multi = next(e for e in attack.catalog if "Multishot Chance" in e.label)
        draft = ComposerDraft(title="Damage then Multishot")
        draft.add_step(DraftStep(kind="ensure_tab", label="Attack", tab="attack"))
        draft.add_step(
            DraftStep(
                kind="seek_and_buy",
                label=damage.label,
                tab="attack",
                catalog_id=damage.id,
                catalog_index=damage.index,
                guards=SeekGuards(),
            )
        )
        draft.add_step(
            DraftStep(
                kind="seek_and_buy",
                label=multi.label,
                tab="attack",
                catalog_id=multi.id,
                catalog_index=multi.index,
                guards=attack.guards_for(multi),
            )
        )
        lines = preview_expansion(draft, self.catalog)
        self.assertTrue(any("Damage" in line for line in lines))

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "events").mkdir()
            (root / "collections").mkdir()
            result = expand_and_write(draft, automations_root=root, catalog=self.catalog)
            self.assertTrue(result.collection_path.exists())
            payload = json.loads(result.collection_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["run"], "once")
            self.assertEqual(len(payload["children"]), 3)
            self.assertGreaterEqual(len(result.event_paths), 2)
            lib = load_library(root)
            self.assertTrue(any(m.get("id") == result.collection_id for m in lib))
            self.assertEqual(lib[-1].get("requires_tab"), "attack")


if __name__ == "__main__":
    unittest.main()
