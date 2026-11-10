"""Molecule Lab — palette gating, conditions, expand/export."""

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
    ConditionAny,
    ConditionLeaf,
    DraftStep,
    SeekGuards,
    StepCondition,
    build_palette,
    outputs_for_step,
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

    def test_empty_context_tabs_sensors_and_nests(self) -> None:
        library = [
            {"id": "mol_atk_pack", "title": "Atk pack", "requires_tab": "attack", "kind": "buy"},
            {"id": "mol_def_pack", "title": "Def pack", "requires_tab": "defense", "kind": "buy"},
        ]
        items = build_palette(
            context=ComposerContext(),
            tabs=self.catalog.tabs,
            library=library,
        )
        self.assertTrue(items)
        self.assertTrue(all(item.kind in {"ensure_tab", "molecule_ref", "event_ref"} for item in items))
        self.assertFalse(any(item.kind == "seek_and_buy" for item in items))
        mol_ids = [item.molecule_id for item in items if item.kind == "molecule_ref"]
        self.assertIn("mol_atk_pack", mol_ids)
        self.assertIn("mol_def_pack", mol_ids)
        self.assertTrue(any(item.event_id == "stat_collect" for item in items if item.kind == "event_ref"))

    def test_attack_context_shows_buys_not_other_tabs(self) -> None:
        ctx = ComposerContext()
        ctx.enter_tab("attack")
        items = build_palette(context=ctx, tabs=self.catalog.tabs, library=[])
        kinds = {item.kind for item in items}
        self.assertIn("seek_and_buy", kinds)
        labels = [item.label for item in items if item.kind == "seek_and_buy"]
        self.assertIn("Damage", labels)
        self.assertNotIn("Health", labels)

    def test_library_molecule_nests_cross_tab(self) -> None:
        ctx = ComposerContext()
        ctx.enter_tab("attack")
        library = [
            {"id": "mol_atk_pack", "title": "Atk pack", "requires_tab": "attack", "kind": "buy"},
            {"id": "mol_def_pack", "title": "Def pack", "requires_tab": "defense", "kind": "buy"},
        ]
        items = build_palette(context=ctx, tabs=self.catalog.tabs, library=library)
        by_group: dict[str, list[str]] = {}
        for item in items:
            if item.kind != "molecule_ref":
                continue
            by_group.setdefault(item.group, []).append(item.molecule_id or "")
        self.assertIn("mol_atk_pack", by_group.get("Nest molecule (this tab)", []))
        self.assertIn("mol_def_pack", by_group.get("Nest molecule (other tab)", []))
        self.assertTrue(any(item.event_id == "stat_collect" for item in items if item.kind == "event_ref"))

    def test_multishot_guards_include_rapid_fire(self) -> None:
        attack = self.catalog.tabs["attack"]
        entry = next(e for e in attack.catalog if "Multishot Chance" in e.label or "Multi" in e.label)
        guards = attack.guards_for(entry)
        joined = " ".join(guards.too_far_down).lower()
        self.assertTrue("rapid" in joined or "bounce" in joined or "multishot" in joined)


class ComposerConditionModelTests(unittest.TestCase):
    def test_migrate_v1_after_prev(self) -> None:
        draft = ComposerDraft.from_dict(
            {
                "title": "Legacy",
                "steps": [
                    {"kind": "ensure_tab", "label": "Attack", "tab": "attack"},
                    {
                        "kind": "seek_and_buy",
                        "label": "Damage",
                        "tab": "attack",
                        "condition": {
                            "variable": "wave",
                            "op": "gte",
                            "value": 1000,
                            "value_hi": None,
                            "after_step": -1,
                            "note": "",
                        },
                    },
                ],
            }
        )
        gate = draft.steps[1].condition
        self.assertIsNotNone(gate)
        assert gate is not None
        self.assertEqual(gate.when_true, "perform")
        self.assertEqual(len(gate.all), 1)
        leaf = gate.all[0]
        self.assertIsInstance(leaf, ConditionLeaf)
        assert isinstance(leaf, ConditionLeaf)
        self.assertEqual(leaf.source_step, 0)
        self.assertEqual(leaf.field, "wave")
        self.assertIn("step 1.wave ≥ 1000", gate.summary())

    def test_migrate_v1_no_previous_drops_gate(self) -> None:
        draft = ComposerDraft.from_dict(
            {
                "title": "Solo",
                "steps": [
                    {
                        "kind": "ensure_tab",
                        "label": "Attack",
                        "tab": "attack",
                        "condition": {
                            "variable": "wave",
                            "op": "gte",
                            "value": 1,
                            "after_step": -1,
                        },
                    }
                ],
            }
        )
        self.assertIsNone(draft.steps[0].condition)

    def test_and_or_summary_and_polarity(self) -> None:
        gate = StepCondition(
            when_true="skip",
            all=[
                ConditionLeaf(source_step=0, field="wave", op="gte", value=150),
                ConditionAny(
                    leaves=[
                        ConditionLeaf(source_step=0, field="wave", op="lt", value=400),
                        ConditionLeaf(source_step=1, field="completed", op="nonempty"),
                    ]
                ),
            ],
        )
        text = gate.summary()
        self.assertIn("when true skip", text)
        self.assertIn("AND", text)
        self.assertIn("OR", text)
        self.assertIn("step 1.wave ≥ 150", text)

    def test_outputs_for_step_kinds(self) -> None:
        tab = DraftStep(kind="ensure_tab", label="Attack", tab="attack")
        self.assertIn("tab_ready", outputs_for_step(tab))
        buy = DraftStep(kind="seek_and_buy", label="Damage", tab="attack")
        self.assertIn("bought", outputs_for_step(buy))
        stats = DraftStep(kind="molecule_ref", label="Stats", molecule_id="stat_collect")
        self.assertIn("wave", outputs_for_step(stats))
        atom = DraftStep(kind="event_ref", label="Stat collect", event_id="stat_collect")
        self.assertIn("wave", outputs_for_step(atom))
        other = DraftStep(kind="molecule_ref", label="Pack", molecule_id="mol_buy_pack")
        self.assertEqual(outputs_for_step(other), ["completed"])

    def test_remove_step_remaps_and_drops_illegal(self) -> None:
        draft = ComposerDraft(title="Remap")
        draft.add_step(DraftStep(kind="ensure_tab", label="Attack", tab="attack"))
        draft.add_step(DraftStep(kind="seek_and_buy", label="Damage", tab="attack"))
        draft.add_step(
            DraftStep(
                kind="seek_and_buy",
                label="Range",
                tab="attack",
                condition=StepCondition(
                    all=[ConditionLeaf(source_step=1, field="bought", op="nonempty")]
                ),
            )
        )
        draft.remove_at(1)
        # Range is now index 1; source Damage was removed → gate dropped.
        self.assertEqual(draft.steps[1].label, "Range")
        self.assertIsNone(draft.steps[1].condition)

    def test_reorder_keeps_valid_source(self) -> None:
        draft = ComposerDraft(title="Ordered")
        draft.add_step(DraftStep(kind="ensure_tab", label="Attack", tab="attack"))
        draft.add_step(
            DraftStep(
                kind="seek_and_buy",
                label="Damage",
                tab="attack",
                condition=StepCondition(
                    all=[ConditionLeaf(source_step=0, field="tab_ready", op="nonempty")]
                ),
            )
        )
        draft.add_step(DraftStep(kind="seek_and_buy", label="Range", tab="attack"))
        self.assertEqual(draft.move_step(2, -1), 1)
        self.assertEqual(draft.steps[1].label, "Range")
        # Damage moved to index 2; source Attack stayed at 0.
        self.assertEqual(draft.steps[2].label, "Damage")
        gate = draft.steps[2].condition
        self.assertIsNotNone(gate)
        assert gate is not None
        leaf = gate.all[0]
        assert isinstance(leaf, ConditionLeaf)
        self.assertEqual(leaf.source_step, 0)
        self.assertIn("tab_ready", draft.steps[2].display_label())


class ComposerDraftTests(unittest.TestCase):
    def test_infer_composite_kind(self) -> None:
        draft = ComposerDraft()
        draft.add_step(DraftStep(kind="molecule_ref", label="A", molecule_id="mol_a"))
        self.assertEqual(draft.kind, "composite")


class ComposerExpandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_capability_catalog(project_root())

    def test_preview_includes_phase_and_condition(self) -> None:
        draft = ComposerDraft(title="Gated buy", phase="midgame", kind="buy")
        draft.add_step(DraftStep(kind="ensure_tab", label="Attack", tab="attack"))
        draft.add_step(
            DraftStep(
                kind="seek_and_buy",
                label="Damage",
                tab="attack",
                catalog_index=0,
                catalog_id="buy.attack.1",
                condition=StepCondition(
                    all=[
                        ConditionLeaf(
                            source_step=0,
                            field="wave",
                            op="between",
                            value=1000,
                            value_hi=1500,
                        )
                    ]
                ),
            )
        )
        lines = preview_expansion(draft, self.catalog)
        blob = "\n".join(lines)
        self.assertIn("midgame", blob)
        self.assertIn("Damage", blob)
        self.assertIn("wave", blob)

    def test_preview_and_export(self) -> None:
        attack = self.catalog.tabs["attack"]
        damage = next(e for e in attack.catalog if e.label == "Damage")
        multi = next(e for e in attack.catalog if "Multishot Chance" in e.label)
        draft = ComposerDraft(title="Damage then Multishot", phase="beginning", kind="buy")
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
                condition=StepCondition(
                    when_true="perform",
                    all=[ConditionLeaf(source_step=0, field="completed", op="nonempty")],
                ),
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
            draft_disk = json.loads(result.draft_path.read_text(encoding="utf-8"))
            self.assertEqual(draft_disk["phase"], "beginning")
            cond = draft_disk["steps"][2].get("condition")
            self.assertIsNotNone(cond)
            self.assertIn("all", cond)
            self.assertEqual(cond["when_true"], "perform")
            # Gate expands to a leading log action on the conditioned buy atom.
            gated = None
            for path in result.event_paths:
                payload_ev = json.loads(path.read_text(encoding="utf-8"))
                actions = payload_ev.get("actions") or []
                if actions and actions[0].get("type") == "log" and "molecule-lab gate" in str(
                    actions[0].get("message") or ""
                ):
                    gated = actions[0]
                    break
            self.assertIsNotNone(gated)
            assert gated is not None
            self.assertIn("Would perform", gated["description"])
            lib = load_library(root)
            self.assertTrue(any(m.get("id") == result.collection_id for m in lib))
            self.assertEqual(
                next(m for m in lib if m.get("id") == result.collection_id).get("requires_tab"),
                "attack",
            )

    def test_v1_draft_roundtrip_migrates_on_load(self) -> None:
        raw = {
            "draft_id": "legacy01",
            "title": "Legacy gate",
            "phase": "beginning",
            "kind": "buy",
            "steps": [
                {"kind": "ensure_tab", "label": "Attack", "tab": "attack"},
                {
                    "kind": "seek_and_buy",
                    "label": "Damage",
                    "tab": "attack",
                    "catalog_id": "buy.attack.1",
                    "catalog_index": 0,
                    "condition": {
                        "variable": "wave",
                        "op": "gte",
                        "value": 1,
                        "value_hi": None,
                        "after_step": -1,
                        "note": "",
                    },
                },
            ],
        }
        draft = ComposerDraft.from_dict(raw)
        dumped = draft.to_dict()
        cond = dumped["steps"][1]["condition"]
        self.assertEqual(cond["when_true"], "perform")
        self.assertEqual(cond["all"][0]["source_step"], 0)
        self.assertEqual(cond["all"][0]["field"], "wave")


if __name__ == "__main__":
    unittest.main()
