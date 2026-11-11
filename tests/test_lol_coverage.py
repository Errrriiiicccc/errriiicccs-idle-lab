"""LOL actuation ↔ atom coverage helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from idle_lab.automations.lol_coverage import (
    build_coverage_rows,
    covering_atoms,
    seed_missing_wrappers,
    stub_event_payload,
    write_stub_atom,
)
from idle_lab.automations.store import AutomationStore
from idle_lab.live_control.playbook import ACTUATION_ACTIONS
from idle_lab.presets import project_root
from idle_lab.shell.atom_create import AtomDraft, build_event_payload, draft_step_from_token, save_atom_draft


class LolCoverageTests(unittest.TestCase):
    def test_live_store_covers_or_seeds(self) -> None:
        store = AutomationStore(project_root() / "automations")
        errors = store.load_all()
        self.assertEqual(errors, [])
        covered = covering_atoms(store)
        for aid in ACTUATION_ACTIONS:
            self.assertIn(aid, covered)
        rows = build_coverage_rows(store)
        statuses = {r.actuation: r.status for r in rows}
        self.assertEqual(statuses.get("stat_collect"), "covered")
        self.assertIn("describe", statuses)
        self.assertEqual(statuses["describe"], "lol_only")

    def test_seed_writes_missing_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = root / "events"
            events.mkdir()
            store = AutomationStore(root)
            store.load_all()
            written = seed_missing_wrappers(store, events)
            self.assertEqual(len(written), len(ACTUATION_ACTIONS))
            store2 = AutomationStore(root)
            store2.load_all()
            again = seed_missing_wrappers(store2, events)
            self.assertEqual(again, [])
            for aid in ACTUATION_ACTIONS:
                self.assertTrue((events / f"lco_{aid}.json").exists())

    def test_stub_payload_is_lco(self) -> None:
        payload = stub_event_payload("buy_3")
        self.assertEqual(payload["id"], "lco_buy_3")
        self.assertEqual(payload["actions"][0]["type"], "lco")
        self.assertEqual(payload["actions"][0]["action"], "buy_3")
        self.assertFalse(payload["enabled"])


class AtomCreatePersistTests(unittest.TestCase):
    def test_draft_keys_and_save(self) -> None:
        self.assertEqual(draft_step_from_token("1"), ("lco", "buy_1"))
        self.assertEqual(draft_step_from_token("K"), ("click", "center"))
        draft = AtomDraft()
        draft.add_lco("tab_attack")
        draft.add_click()
        draft.event_id = "atom_unit_test"
        with tempfile.TemporaryDirectory() as tmp:
            path = save_atom_draft(Path(tmp), draft)
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("tab_attack", text)
            self.assertIn("click", text)

    def test_no_silent_empty_save(self) -> None:
        with self.assertRaises(ValueError):
            build_event_payload(event_id="x", title="x", steps=[])


if __name__ == "__main__":
    unittest.main()
