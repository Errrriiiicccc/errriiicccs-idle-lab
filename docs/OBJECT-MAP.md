# Object map (Tower-first templates)

**Status:** v1 2026-11-08  
**Canonical file:** [`automations/maps/tower_main_gameplay.objects.json`](../automations/maps/tower_main_gameplay.objects.json)  
**Shim:** [`automations/playbooks/tower_main_gameplay.json`](../automations/playbooks/tower_main_gameplay.json) → points at the object map  
**Related:** [LIVE-CONTROL-OVERLAY.md](LIVE-CONTROL-OVERLAY.md), [GAMEPLAY-TEST.md](GAMEPLAY-TEST.md), [VISION.md](VISION.md) §5

Live Control Overlay no longer thinks in a flat click sheet. It loads a **typed object graph**: kind templates (what a thing *is*) + filled instances (where it lives in The Tower).

## Kind templates

| Kind | Role |
| --- | --- |
| `button` | Clickable; optional key; world and/or UI effects |
| `tab_button` | Opens/replaces a `panel`; rule `no_retap_if_active` |
| `panel` | Region that hosts children (scroll lists) |
| `scroll_list` | Drag-scrollable; calibrated row physics; contains buy slots |
| `buy_button` | Spends cash, upgrades a named stat; visual states max/affordable/unaffordable |

**Template** = reusable kind + required slots.  
**Instance** = one filled object (`tab.attack`, `list.defense`, `buy.attack.1`, …).

Containment is first-class: tab → panel → scroll list → buy buttons.

## What LCO reads

- Hotkeys stay Q/W/E, 1–6, R/F, V, B.
- Tabs resolve to `tab_button` hits + `open_panel` effects.
- Scroll uses the open tab’s `scroll_list` (`scroll_ref` → shared `upgrade_list_scroll`).
- Buys resolve to `buy_button` instances (label + effects); live detection still re-parks 1–6 on screen.
- Evidence rows carry `object_id` / `effects` when the map is loaded.

Code: `src/idle_lab/live_control/objects.py` → projects to `LiveControlPlaybook` for the overlay.

## Observe → template fill (thin bridge)

No auto-mapper yet. Observation **fills slots** on these templates.

1. **Start observation** (deck **O → 1**) on main gameplay.
2. Walk the UI you care about: open each upgrade tab, scroll a row or two, tap a buy you can afford and one you cannot (if safe), Mark key frames.
3. From `DIGEST.md` + a handful of PNGs, fill or correct object-map fields:

| Evidence | Map slot |
| --- | --- |
| Tab click locus | `tab_*.hit` |
| Panel bounds when open | `panel.*.roi` |
| Card size / 2×3 pitch | `shared.buy_grid` |
| Row drag that advances one tile | `shared.upgrade_list_scroll.drag_fraction` (R/F); fling uses `fling_fraction` (T/G) |
| First-page labels | `list.*.page_labels` + matching `buy_*.label` / `stat` |
| Buy tile colors (max / can buy / can’t) | `shared.buy_visual_states` (RGB TBD until cropped) |
| What a buy does | `buy_*.effects.world` / `.ui` |

4. **Restart** Idle Lab (or Refresh if only JSON data changed) → **U → 1** → verify circles land on the named objects.
5. Misses should name an object (`buy.attack.1`, `list.defense`), not a vibes tweak to a lone `origin_ny`.

Refined observation mode (crop the tile/list ROI instead of the full window) is the next evidence step — see [GAMEPLAY-TEST.md](GAMEPLAY-TEST.md) “Refined”. Semantic action rows (`upgrade.buy`, `nav.defense`) come after the map is trusted.

## Humanize

Precision path defaults to **Off** lab-wide. LCO still forces Off regardless of the chrome menu.
