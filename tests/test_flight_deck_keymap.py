import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.flight_deck.keymap import KeymapError, FlightDeckKeymap, load_keymap
from idle_lab.flight_deck.keys import DEFAULT_EXPAND_VK, menu_token_from_vk, vk_label, vk_from_menu_token
from idle_lab.models import Settings
from idle_lab.settings_store import load_settings, save_settings


class FlightDeckKeymapTests(unittest.TestCase):
    def test_load_sample_tree(self) -> None:
        payload = {
            "version": 1,
            "roots": [
                {
                    "key": "S",
                    "label": "Image",
                    "children": [
                        {
                            "key": "1",
                            "label": "Capture shot",
                            "action": {"type": "observe_shot"},
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "keymap.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            keymap = load_keymap(path)
            self.assertIsInstance(keymap, FlightDeckKeymap)
            self.assertEqual(len(keymap.roots), 1)
            node = keymap.child_for_key(keymap.roots, "s")
            self.assertIsNotNone(node)
            assert node is not None
            leaf = keymap.child_for_key(node.children, "1")
            self.assertIsNotNone(leaf)
            assert leaf is not None
            self.assertTrue(leaf.is_leaf)
            self.assertEqual(leaf.action["type"], "observation_mark")

    def test_rejects_branch_with_action(self) -> None:
        payload = {
            "version": 1,
            "roots": [
                {
                    "key": "S",
                    "label": "Image",
                    "action": {"type": "observe_shot"},
                    "children": [
                        {"key": "1", "label": "A", "action": {"type": "observe_end"}}
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "keymap.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(KeymapError):
                load_keymap(path)

    def test_rejects_stub_action(self) -> None:
        payload = {
            "version": 1,
            "roots": [
                {
                    "key": "Space",
                    "label": "Bad",
                    "action": {"type": "stub", "id": "nope"},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "keymap.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(KeymapError):
                load_keymap(path)


class FlightDeckAccordionTests(unittest.TestCase):
    def test_letter_digit_chord(self) -> None:
        import customtkinter as ctk

        from idle_lab.flight_deck.keys import normalize_menu_key
        from idle_lab.flight_deck.keymap import default_keymap_path, load_keymap
        from idle_lab.flight_deck.window import FlightDeckWindow
        from idle_lab.presets import project_root

        root = ctk.CTk()
        root.withdraw()
        deck = FlightDeckWindow(
            root,
            on_close=lambda: None,
            on_expand_toggle=lambda: None,
            on_pause=lambda: None,
            on_stop=lambda: None,
        )
        try:
            keymap = load_keymap(default_keymap_path(project_root()))
            deck.set_keymap(keymap)
            deck.set_expanded(True)
            self.assertIsNone(deck.navigate("O"))  # open Observe
            self.assertEqual(normalize_menu_key(deck.open_menu_key or ""), "O")
            action = deck.navigate("2")
            self.assertIsNotNone(action)
            assert action is not None
            self.assertEqual(action["type"], "observation_mark")
            self.assertIsNone(deck.navigate("C"))  # switch to Clicks
            self.assertEqual(normalize_menu_key(deck.open_menu_key or ""), "C")
            self.assertIsNone(deck.navigate("C"))  # same letter collapses section
            self.assertIsNone(deck.open_menu_key)
        finally:
            deck.destroy()
            root.destroy()


class FlightDeckKeyHelpersTests(unittest.TestCase):
    def test_backtick_round_trip(self) -> None:
        self.assertEqual(vk_label(DEFAULT_EXPAND_VK), "`")
        self.assertEqual(vk_from_menu_token("`"), DEFAULT_EXPAND_VK)
        self.assertEqual(menu_token_from_vk(DEFAULT_EXPAND_VK), "`")

    def test_letter_and_digit(self) -> None:
        self.assertEqual(vk_from_menu_token("S"), ord("S"))
        self.assertEqual(menu_token_from_vk(ord("S")), "S")
        self.assertEqual(vk_from_menu_token("3"), ord("3"))

    def test_space_token(self) -> None:
        from idle_lab.flight_deck.keys import normalize_menu_key, VK_SPACE

        self.assertEqual(normalize_menu_key("Space"), "SPACE")
        self.assertEqual(normalize_menu_key(" "), "SPACE")
        self.assertEqual(vk_from_menu_token("Space"), VK_SPACE)
        self.assertEqual(menu_token_from_vk(VK_SPACE), "Space")


class FlightDeckGeometryTests(unittest.TestCase):
    def test_rejects_withdrawn_coords(self) -> None:
        from idle_lab.flight_deck.window import parse_geometry, sanitize_geometry

        self.assertIsNone(parse_geometry("280x120+-32000+-32000"))
        self.assertIsNone(sanitize_geometry("nope"))

    def test_clamps_far_right(self) -> None:
        from idle_lab.flight_deck.window import sanitize_geometry
        from idle_lab import win32_api

        screen = win32_api.virtual_screen()
        cleaned = sanitize_geometry(f"320x280+{screen.right + 500}+3")
        self.assertIsNotNone(cleaned)
        assert cleaned is not None
        # Must not stay past the right edge with no visible pixels.
        self.assertNotIn(f"+{screen.right + 500}+", cleaned)


class FlightDeckSettingsTests(unittest.TestCase):
    def test_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            settings = Settings(
                flight_deck_expand_vk=0xC0,
                flight_deck_expand_by_anchor={"BlueStacks App Player": 0xC0},
                flight_deck_geometry="280x120+10+10",
                flight_deck_user_hidden=True,
                last_anchor_title="BlueStacks App Player",
            )
            save_settings(path, settings)
            loaded, err = load_settings(path)
            self.assertIsNone(err)
            self.assertEqual(loaded.flight_deck_expand_vk, 0xC0)
            self.assertEqual(
                loaded.flight_deck_expand_by_anchor.get("BlueStacks App Player"),
                0xC0,
            )
            self.assertEqual(loaded.flight_deck_geometry, "280x120+10+10")
            self.assertTrue(loaded.flight_deck_user_hidden)
            self.assertEqual(loaded.last_anchor_title, "BlueStacks App Player")


if __name__ == "__main__":
    unittest.main()
