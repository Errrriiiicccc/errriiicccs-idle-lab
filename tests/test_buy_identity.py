"""Catalog ↔ viewport buy identity helpers."""

from __future__ import annotations

import unittest

from idle_lab.live_control.buy_identity import (
    bind_by_offset,
    bind_from_slot_texts,
    match_ocr_to_catalog,
    nameplate_roi,
    next_offset,
    parse_catalog,
    unknown_identity,
)
from idle_lab.live_control.objects import default_object_map_path, load_object_map
from idle_lab.presets import project_root


class BuyIdentityUnitTests(unittest.TestCase):
    def test_parse_and_bind_offset(self) -> None:
        catalog = parse_catalog(
            [
                {"id": "a", "label": "Damage", "column": "left"},
                {"id": "b", "label": "Atk Speed", "column": "right"},
                {"id": "c", "label": "Crit Chance", "column": "left"},
                {"id": "d", "label": "Crit Factor", "column": "right"},
                {"id": "e", "label": "Range", "column": "left"},
                {"id": "f", "label": "Dmg/Meter", "column": "right"},
                {"id": "g", "label": "Multishot Chance", "column": "left"},
                {"id": "h", "label": "Multishot Targets", "column": "right"},
            ]
        )
        top = bind_by_offset(catalog, offset=0, slot_count=6)
        self.assertTrue(top.known)
        self.assertEqual(top.label_for(1), "Damage")
        self.assertEqual(top.label_for(6), "Dmg/Meter")

        mid = bind_by_offset(catalog, offset=2, slot_count=6)
        self.assertTrue(mid.known)
        self.assertEqual(mid.label_for(1), "Crit Chance")
        self.assertEqual(mid.label_for(5), "Multishot Chance")
        self.assertEqual(mid.binding_for(5).object_id, "g")

    def test_next_offset_advances_by_row(self) -> None:
        self.assertEqual(next_offset(0, direction="down", rows=1, cols=2, catalog_len=13), 2)
        self.assertEqual(next_offset(2, direction="up", rows=1, cols=2, catalog_len=13), 0)
        self.assertIsNone(next_offset(12, direction="down", rows=1, cols=2, catalog_len=13))

    def test_unknown_identity_is_honest(self) -> None:
        view = unknown_identity(6, reason="scroll-lost")
        self.assertFalse(view.known)
        self.assertEqual(view.label_for(1), "?")
        self.assertIsNone(view.binding_for(1).object_id)

    def test_ocr_match_uses_aliases_and_abstains_on_ambiguity(self) -> None:
        catalog = parse_catalog(
            [
                {"id": "a", "label": "Atk Speed", "aliases": ["Attack Speed"], "column": "right"},
                {"id": "b", "label": "Crit Chance", "aliases": ["Critical Chance"], "column": "left"},
                {"id": "c", "label": "Crit Factor", "aliases": ["Critical Factor"], "column": "right"},
            ]
        )
        hit = match_ocr_to_catalog("Attack Speed", catalog, column="right")
        assert hit is not None
        self.assertEqual(hit.entry.id, "a")

        # Ambiguous "Crit" against two Crit* entries → abstain.
        self.assertIsNone(match_ocr_to_catalog("Crit", catalog))

    def test_bind_from_slot_texts_recovers_overshot_defense_row(self) -> None:
        # Real failure: scroll math said Defense % under key 1; cards were Thorn…
        omap_catalog = load_object_map(default_object_map_path(project_root())).catalog_for_tab("defense")
        view = bind_from_slot_texts(
            omap_catalog,
            {
                1: "Thorn Damage",
                2: "Lifesteal",
                3: "Knockback Chance",
                4: "Knockback Force",
            },
            slot_count=6,
        )
        self.assertTrue(view.known)
        self.assertEqual(view.offset, 4)
        self.assertEqual(view.label_for(1), "Thorn")
        self.assertEqual(view.label_for(2), "Lifesteal")
        self.assertEqual(view.label_for(3), "Knockback Chance")
        self.assertEqual(view.label_for(5), "Orb Speed")
        self.assertGreaterEqual(view.confidence, 0.55)

    def test_partial_ocr_anchors_fill_neighbors_from_structure(self) -> None:
        """Thorn+Lifesteal OCR alone should lock Knockback below (and not claim Defense %)."""

        omap_catalog = load_object_map(default_object_map_path(project_root())).catalog_for_tab("defense")
        view = bind_from_slot_texts(
            omap_catalog,
            {
                1: "Thorn Damagc",  # noisy OCR
                2: "Lifesteai",
                3: "??? garbage ???",
                4: "",
                5: "noise",
                6: "",
            },
            slot_count=6,
        )
        self.assertTrue(view.known)
        self.assertEqual(view.offset, 4)
        self.assertEqual(view.label_for(1), "Thorn")
        self.assertEqual(view.label_for(2), "Lifesteal")
        self.assertEqual(view.label_for(3), "Knockback Chance")
        self.assertEqual(view.label_for(4), "Knockback Force")
        self.assertEqual(view.binding_for(3).source, "structure")
        self.assertGreaterEqual(view.binding_for(3).confidence, 0.35)
        self.assertNotEqual(view.label_for(1), "Defense %")
        # Hold-D markers: strong OCR plain, structure often ~ / ?
        self.assertIn(view.binding_for(1).display_label[0], "T")
        self.assertTrue(view.offset_scores)

    def test_single_crit_chance_anchor_fills_attack_window(self) -> None:
        """Live failure: only Crit Chance OCR'd; rest were Max-plate garbage / empty."""

        attack = load_object_map(default_object_map_path(project_root())).catalog_for_tab("attack")
        view = bind_from_slot_texts(
            attack,
            {
                1: "Critical Chance",
                2: "Max",
                3: "56.00%",
                4: "",
                5: "x5",
                6: "|||",
            },
            slot_count=6,
        )
        self.assertTrue(view.known)
        self.assertEqual(view.offset, 2)
        self.assertEqual(view.label_for(1), "Crit Chance")
        self.assertEqual(view.label_for(2), "Crit Factor")
        self.assertEqual(view.label_for(3), "Range")
        self.assertEqual(view.label_for(4), "Dmg/Meter")
        self.assertEqual(view.label_for(5), "Multishot Chance")
        self.assertEqual(view.binding_for(2).source, "structure")

    def test_nameplate_roi_sits_left_of_click(self) -> None:
        roi = nameplate_roi(0.32, 0.74)
        self.assertLess(roi["nx"], 0.32)
        self.assertAlmostEqual(roi["nx"], 0.08, places=2)
        self.assertLess(roi["ny"], 0.74)
        self.assertGreater(roi["nw"], 0.1)


class ObjectMapCatalogTests(unittest.TestCase):
    def test_tower_map_has_full_attack_catalog(self) -> None:
        omap = load_object_map(default_object_map_path(project_root()))
        attack = omap.catalog_for_tab("attack")
        self.assertGreaterEqual(len(attack), 10)
        self.assertEqual(attack[0].label, "Damage")
        self.assertEqual(attack[6].label, "Multishot Chance")
        self.assertTrue(attack[6].provisional)
        defense = omap.catalog_for_tab("defense")
        self.assertEqual(defense[6].label, "Knockback Chance")
        self.assertEqual(defense[10].label, "Shockwave Size")
        self.assertEqual(defense[14].label, "Land Mine Radius")
        self.assertEqual(len(defense), 15)
        utility = omap.catalog_for_tab("utility")
        self.assertEqual(utility[6].label, "Free Utility Up")
        scroll = omap.scroll_params("defense")
        self.assertEqual(int(scroll.get("hold_end_ms") or 0), 450)


if __name__ == "__main__":
    unittest.main()
