import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.automations.store import AutomationStore
from idle_lab.flight_deck.keymap import default_keymap_path, load_keymap
from idle_lab.presets import PresetStore, project_root
from idle_lab.taxonomy import (
    TaxonomyError,
    default_taxonomy_path,
    find_node,
    listed_ref_ids,
    load_taxonomy,
    resolve_taxonomy,
    with_unfiled,
)


class TaxonomyLoadTests(unittest.TestCase):
    def test_shipped_taxonomy_resolves(self) -> None:
        root = project_root()
        auto = AutomationStore(root / "automations")
        self.assertEqual(auto.load_all(), [])
        presets = PresetStore(root / "presets")
        self.assertEqual(presets.load_all(), [])
        taxonomy = load_taxonomy(default_taxonomy_path(root))
        resolved = resolve_taxonomy(
            taxonomy,
            event_ids=auto.events.keys(),
            collection_ids=auto.collections.keys(),
            preset_names={preset.name for preset in presets.presets},
        )
        self.assertIsNotNone(find_node(resolved, "loops.events"))
        self.assertIsNotNone(find_node(resolved, "loops.collections"))
        self.assertIsNotNone(find_node(resolved, "screen_map"))
        atoms = find_node(resolved, "loops.events")
        assert atoms is not None
        self.assertEqual(atoms.label, "Atoms")

    def test_shipped_flight_deck_catalog(self) -> None:
        root = project_root()
        keymap = load_keymap(default_keymap_path(root))
        labels = [node.label for node in keymap.roots]
        self.assertEqual(labels, ["Observe", "Clicks", "Nav", "Atoms", "Molecules"])
        keys = [node.key.upper() for node in keymap.roots]
        self.assertEqual(keys, ["O", "C", "N", "A", "M"])
        observe = keymap.child_for_key(keymap.roots, "O")
        assert observe is not None
        shot = keymap.child_for_key(observe.children, "2")
        assert shot is not None
        self.assertEqual(shot.action["type"], "observe_shot")
        # No Space flagship on the deck catalog.
        for root_node in keymap.roots:
            self.assertNotEqual(root_node.key.strip().lower(), "space")
            for child in root_node.children:
                self.assertNotEqual(child.key.strip().lower(), "space")

    def test_rejects_reserved_key(self) -> None:
        payload = {
            "version": 1,
            "roots": [
                {
                    "id": "bad",
                    "key": "X",
                    "label": "Nope",
                    "action": {"type": "observe_end"},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "taxonomy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(TaxonomyError):
                load_taxonomy(path)

    def test_rejects_unknown_event_ref(self) -> None:
        payload = {
            "version": 1,
            "roots": [
                {
                    "id": "r",
                    "key": "Space",
                    "label": "Root",
                    "children": [
                        {
                            "id": "r.leaf",
                            "key": "Space",
                            "label": "Missing",
                            "ref": {"kind": "event", "id": "no_such_event"},
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "taxonomy.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            taxonomy = load_taxonomy(path)
            with self.assertRaises(TaxonomyError):
                resolve_taxonomy(
                    taxonomy,
                    event_ids=[],
                    collection_ids=[],
                    preset_names=[],
                )

    def test_unfiled_appends_missing(self) -> None:
        root = project_root()
        auto = AutomationStore(root / "automations")
        auto.load_all()
        taxonomy = load_taxonomy(default_taxonomy_path(root))
        events_root = find_node(taxonomy, "loops.events")
        self.assertIsNotNone(events_root)
        assert events_root is not None
        # Pretend an extra event exists on disk.
        enriched = with_unfiled(
            events_root,
            kind="event",
            all_ids=list(auto.events.keys()) + ["ghost_event"],
            titles={"ghost_event": "Ghost"},
        )
        listed = listed_ref_ids(enriched, "event")
        self.assertIn("ghost_event", listed)
        unfiled = next(child for child in enriched.children if child.id.endswith(".unfiled"))
        self.assertEqual(unfiled.label, "Unfiled")


class LegacyKeymapGoneTests(unittest.TestCase):
    def test_old_keymap_file_removed(self) -> None:
        path = project_root() / "automations" / "flight_deck_keymap.json"
        self.assertFalse(path.exists())

    def test_flight_deck_json_present(self) -> None:
        self.assertTrue((project_root() / "automations" / "flight_deck.json").is_file())


if __name__ == "__main__":
    unittest.main()
