import unittest

from idle_lab.automations.collections_runner import (
    expand_collection_children,
    should_stop_collection,
)
from idle_lab.automations.schema import Collection
from idle_lab.automations.store import AutomationStore


class CollectionRunnerHelpersTests(unittest.TestCase):
    def test_stop_when_game_over(self) -> None:
        coll = Collection(id="c", title="c", stop_when="game_over")
        self.assertFalse(should_stop_collection(coll, {}, {}))
        self.assertTrue(should_stop_collection(coll, {"game_over": "GAME_OVER"}, {}))
        self.assertTrue(should_stop_collection(coll, {}, {"game_over": True}))

    def test_branch_expands(self) -> None:
        coll = Collection(
            id="c",
            title="c",
            children=["a", "b"],
            branches={"mid": "b"},
            branch_variable="phase",
        )
        store = AutomationStore.__new__(AutomationStore)
        store.events = {}
        store.collections = {}
        self.assertEqual(expand_collection_children(coll, store, {"phase": "mid"}), ["b"])
        self.assertEqual(expand_collection_children(coll, store, {}), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
