"""Phase map Atom Create — leaves, scroll=drag, expand like tab→buy."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.shell.atom_create import AtomDraft, step_label
from idle_lab.shell.atom_phase_map import (
    ROLE_SCROLL,
    ROLE_TARGET,
    add_enter_key,
    add_scroll_def,
    add_target,
    build_atom_kind_keymap,
    build_phase_map_edit_keymap,
    build_phase_map_keymap,
    expand_preview_lines,
    expand_target_actions,
    expand_target_event,
    format_phase_tree_lines,
    queue_piece_line,
    register_phase,
    save_phase_map_draft,
    set_parent_phase,
)


class AtomPhaseMapTests(unittest.TestCase):
    def test_kind_gate_has_both_kinds(self) -> None:
        km = build_atom_kind_keymap()
        keys = {n.key for n in km.roots}
        self.assertEqual(keys, {"1", "2"})
        types = {n.action["type"] for n in km.roots if n.action}
        self.assertEqual(types, {"atom_kind_automation", "atom_kind_phase_map"})

    def test_phase_map_roots_cover_menu_navigation(self) -> None:
        draft = AtomDraft(kind="phase_map")
        km = build_phase_map_keymap(draft=draft)
        roots = {n.key.upper() for n in km.roots}
        self.assertTrue({"G", "H", "T", "S", "R", "A", "E", "X"}.issubset(roots))
        g = next(n for n in km.roots if n.key.upper() == "G")
        self.assertGreaterEqual(len(g.children), 4)
        t = next(n for n in km.roots if n.key.upper() == "T")
        kinds = {c.action.get("target_kind") for c in t.children if c.action and "target_kind" in c.action}
        self.assertIn("equip", kinds)
        self.assertIn("buy", kinds)
        s = next(n for n in km.roots if n.key.upper() == "S")
        scroll_types = {c.action["type"] for c in s.children if c.action}
        self.assertIn("pm_add_scroll", scroll_types)

    def test_phase_pickers_are_hotkey_leaves(self) -> None:
        draft = AtomDraft(kind="phase_map")
        register_phase(draft, "options_rail")
        register_phase(draft, "cards", parent="options_rail")
        draft.active_phase = "cards"
        km = build_phase_map_keymap(draft=draft)
        h = next(n for n in km.roots if n.key.upper() == "H")
        by_key = {c.key: c for c in h.children}
        active = by_key["2"]
        self.assertTrue(active.children)
        active_types = {c.action["type"] for c in active.children if c.action}
        self.assertEqual(active_types, {"pm_pick_active"})
        parent = by_key["3"]
        parent_ids = {c.action.get("phase_id") for c in parent.children if c.action}
        self.assertIn("", parent_ids)  # root
        self.assertIn("options_rail", parent_ids)
        self.assertNotIn("cards", parent_ids)  # exclude self

    def test_scroll_def_is_drag_with_same_edit_leaves(self) -> None:
        draft = AtomDraft(kind="phase_map")
        register_phase(draft, "cards")
        add_scroll_def(draft)
        step = draft.steps[0]
        self.assertEqual(step["type"], "drag")
        self.assertEqual(step["role"], ROLE_SCROLL)
        self.assertIn("speed", step)
        self.assertIn("pause_end", step)
        edit = build_phase_map_edit_keymap(
            step_count=1, selected_index=0, selected_step=step
        )
        types = {n.action["type"] for n in edit.roots if n.action}
        self.assertIn("atom_edit_drag_cycle_speed", types)
        self.assertIn("atom_edit_drag_toggle_pause", types)
        self.assertIn("pm_name_scroll", types)

    def test_cards_equip_free_upgrades_includes_scroll(self) -> None:
        draft = AtomDraft(kind="phase_map", event_id="phase_map_cards")
        register_phase(draft, "options_rail")
        register_phase(draft, "cards", parent="options_rail")
        draft.active_phase = "options_rail"
        add_enter_key(draft, via="click")
        draft.steps[-1]["nx"] = 0.89
        draft.steps[-1]["ny"] = 0.06
        draft.active_phase = "cards"
        add_enter_key(draft, via="click")
        draft.steps[-1]["nx"] = 0.82
        draft.steps[-1]["ny"] = 0.28
        add_scroll_def(draft)
        draft.steps[-1]["scroll_id"] = "inventory_down"
        draft.steps[-1]["nx0"] = 0.5
        draft.steps[-1]["ny0"] = 0.72
        draft.steps[-1]["nx1"] = 0.5
        draft.steps[-1]["ny1"] = 0.52
        add_target(draft, target_kind="equip")
        tgt = draft.steps[-1]
        tgt["label"] = "Free Upgrades"
        tgt["target_id"] = "free_upgrades"
        tgt["scrolls"] = ["inventory_down"]
        tgt["nx"] = 0.2
        tgt["ny"] = 0.62

        actions = expand_target_actions(draft, tgt)
        self.assertEqual(len(actions), 4)  # rail enter, cards enter, scroll, click
        self.assertEqual(actions[0]["type"], "click")
        self.assertEqual(actions[1]["type"], "click")
        self.assertEqual(actions[2]["type"], "drag")
        self.assertAlmostEqual(float(actions[2]["ny0"]), 0.72)
        self.assertAlmostEqual(float(actions[2]["ny1"]), 0.52)
        self.assertEqual(actions[3]["type"], "click")
        self.assertNotIn("role", actions[2])
        self.assertNotIn("scrolls", actions[3])

        ev = expand_target_event(draft, tgt, map_id="phase_map_cards")
        self.assertEqual(ev["kind"], "automation")
        self.assertEqual(ev["id"], "phase_map_cards__free_upgrades")
        self.assertEqual(len(ev["actions"]), 4)

        preview = expand_preview_lines(draft, tgt)
        self.assertTrue(any("Free Upgrades" in line for line in preview))
        self.assertEqual(step_label(tgt), "equip:Free Upgrades")

    def test_save_expands_target_atoms(self) -> None:
        draft = AtomDraft(kind="phase_map", event_id="phase_map_cards")
        register_phase(draft, "cards")
        add_enter_key(draft, via="click")
        add_scroll_def(draft)
        draft.steps[-1]["scroll_id"] = "inventory_down"
        add_target(draft, target_kind="equip")
        draft.steps[-1]["target_id"] = "free_upgrades"
        draft.steps[-1]["label"] = "Free Upgrades"
        draft.steps[-1]["scrolls"] = ["inventory_down"]
        with tempfile.TemporaryDirectory() as tmp:
            path, expanded = save_phase_map_draft(Path(tmp), draft, expand_targets=True)
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["kind"], "phase_map")
            self.assertEqual(len(expanded), 1)
            child = json.loads(expanded[0].read_text(encoding="utf-8"))
            self.assertEqual(child["source_phase_map"], "phase_map_cards")
            kinds = [a["type"] for a in child["actions"]]
            self.assertEqual(kinds, ["click", "drag", "click"])

    def test_queue_shows_phase_tree_and_role_lines(self) -> None:
        draft = AtomDraft(kind="phase_map")
        register_phase(draft, "options_rail")
        register_phase(draft, "cards", parent="options_rail")
        draft.home_phase = "cards"
        draft.active_phase = "cards"
        tree = format_phase_tree_lines(
            draft.phases, home_phase="cards", active_phase="cards"
        )
        joined = "\n".join(tree)
        self.assertIn("options_rail", joined)
        self.assertIn("cards", joined)
        self.assertIn("home", joined)
        self.assertIn("active", joined)
        add_target(draft, target_kind="equip")
        draft.steps[-1]["label"] = "Free Upgrades"
        draft.steps[-1]["scrolls"] = ["inventory_down"]
        line = queue_piece_line(draft.steps[-1], index=0, selected=True)
        self.assertIn("Free Upgrades", line)
        self.assertIn("inventory_down", line)
        self.assertTrue(line.startswith("▶"))

    def test_sample_cards_file_loads(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sample = root / "automations" / "events" / "phase_map_cards.json"
        data = json.loads(sample.read_text(encoding="utf-8"))
        self.assertEqual(data["kind"], "phase_map")
        draft = AtomDraft(
            kind="phase_map",
            event_id=data["id"],
            title=data["title"],
            steps=list(data["pieces"]),
            phases=list(data["phases"]),
            home_phase=str(data.get("home_phase") or ""),
            active_phase="cards",
        )
        set_parent_phase(draft, "cards", "options_rail")
        tgt = next(s for s in draft.steps if s.get("target_id") == "free_upgrades")
        self.assertEqual(tgt["role"], ROLE_TARGET)
        actions = expand_target_actions(draft, tgt)
        self.assertGreaterEqual(len(actions), 3)
        self.assertTrue(any(a.get("type") == "drag" for a in actions))


if __name__ == "__main__":
    unittest.main()
