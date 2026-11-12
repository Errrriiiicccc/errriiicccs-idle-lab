"""Atom Create draft edit helpers + keymap."""

from __future__ import annotations

import unittest

from idle_lab.shell.atom_create import (
    AtomDraft,
    build_atom_create_keymap,
    build_atom_edit_keymap,
    build_atom_playbook_keymap,
    step_label,
)


class AtomCreateEditTests(unittest.TestCase):
    def test_select_and_reorder(self) -> None:
        draft = AtomDraft()
        draft.add_lco("buy_1")
        draft.add_click(nx=0.2, ny=0.3)
        draft.add_lco("claim_gem")
        self.assertEqual(draft.selected_index, 2)
        draft.select_delta(-1)
        self.assertEqual(draft.selected_index, 1)
        draft.move_selected(-1)
        self.assertEqual(draft.selected_index, 0)
        self.assertEqual(draft.steps[0]["type"], "click")
        self.assertEqual(draft.steps[1]["action"], "buy_1")

    def test_set_click_norm(self) -> None:
        draft = AtomDraft()
        draft.add_click()
        draft.set_click_norm(0, nx=0.8, ny=0.1)
        self.assertAlmostEqual(draft.steps[0]["nx"], 0.8)
        self.assertAlmostEqual(draft.steps[0]["ny"], 0.1)
        self.assertEqual(step_label(draft.steps[0]), "click")
        from idle_lab.shell.atom_create import step_detail_lines

        details = "\n".join(step_detail_lines(draft.steps[0]))
        self.assertIn("0.80", details)
        self.assertIn("mode single", details)

    def test_edit_keymap_has_remove_and_modes(self) -> None:
        draft = AtomDraft()
        draft.add_click()
        edit = build_atom_edit_keymap(
            step_count=1, selected_index=0, selected_step=draft.steps[0]
        )
        kinds = {n.action["type"] for n in edit.roots if n.action}
        self.assertIn("atom_edit_remove", kinds)
        self.assertIn("atom_edit_toggle_mode", kinds)
        draft.toggle_fire_mode(0)
        edit_spam = build_atom_edit_keymap(
            step_count=1, selected_index=0, selected_step=draft.steps[0]
        )
        spam_kinds = {n.action["type"] for n in edit_spam.roots if n.action}
        self.assertIn("atom_edit_toggle_spam_by", spam_kinds)
        self.assertIn("atom_edit_ask_click_amount", spam_kinds)
        self.assertIn("atom_edit_ask_interval", spam_kinds)

    def test_snap_timed_spam_duration(self) -> None:
        from idle_lab.shell.atom_create import snap_spam_duration_ms, spam_click_count

        self.assertEqual(spam_click_count(duration_ms=100, interval_ms=30), 4)
        self.assertEqual(snap_spam_duration_ms(100, 30), 90)
        self.assertEqual(snap_spam_duration_ms(100, 50), 100)
        draft = AtomDraft()
        draft.add_click()
        draft.toggle_fire_mode(0)
        draft.toggle_spam_by(0)  # timed
        draft.set_spam_duration_ms(0, 100)
        draft.set_spam_interval_ms(0, 30)
        changed = draft.snap_timed_spam_fields()
        self.assertEqual(changed, [0])
        self.assertEqual(draft.steps[0]["duration_ms"], 90)

    def test_edit_keymap_leaves(self) -> None:
        create = build_atom_create_keymap(step_count=1)
        root_keys = {n.key.upper() for n in create.roots}
        self.assertEqual(root_keys, {"B", "P", "E"})
        basic = next(n for n in create.roots if n.key.upper() == "B")
        self.assertFalse(basic.is_leaf)
        self.assertIn("Basic Gesture", basic.label)
        gesture_kinds = {c.action["type"] for c in basic.children if c.action}
        self.assertEqual(
            gesture_kinds,
            {"atom_add_click", "atom_add_drag", "atom_add_key", "atom_add_ocr"},
        )
        playbook_leaf = next(n for n in create.roots if n.key.upper() == "P")
        self.assertTrue(playbook_leaf.is_leaf)
        self.assertEqual(playbook_leaf.action["type"], "atom_playbook_enter")
        playbook = build_atom_playbook_keymap(step_count=1)
        play_sections = {c.key.upper() for c in playbook.roots}
        self.assertEqual(play_sections, {"B", "T", "S", "U"})
        edit = build_atom_edit_keymap(step_count=3, selected_index=1)
        kinds = {n.action["type"] for n in edit.roots if n.action}
        self.assertTrue(
            {
                "atom_edit_prev",
                "atom_edit_next",
                "atom_edit_move_up",
                "atom_edit_move_down",
                "atom_edit_remove",
                "atom_edit_exit",
            }.issubset(kinds)
        )

    def test_drag_key_ocr_labels(self) -> None:
        draft = AtomDraft()
        draft.add_drag(nx0=0.1, ny0=0.2, nx1=0.3, ny1=0.4)
        draft.add_key("Enter")
        draft.add_ocr(nx=0.2, ny=0.2, nw=0.25, nh=0.1)
        draft.set_drag_norm(0, which="end", nx=0.9, ny=0.8)
        self.assertAlmostEqual(draft.steps[0]["nx1"], 0.9)
        self.assertIn("drag", step_label(draft.steps[0]))
        self.assertIn("key:Enter", step_label(draft.steps[1]))
        self.assertIn("ocr", step_label(draft.steps[2]))


if __name__ == "__main__":
    unittest.main()
