# Live Control Overlay

**Status:** v1 + object map 2026-11-08  
**Enter:** flight deck **U → 1** (play) or **U → 2** (troubleshoot)  
**Exit:** Esc (deck shows Exit LCO while active; Activate/Deactivate blocked until LCO exits)  
**Object map:** [`automations/maps/tower_main_gameplay.objects.json`](../automations/maps/tower_main_gameplay.objects.json)  
**Detail:** [OBJECT-MAP.md](OBJECT-MAP.md)

Keyboard-driven overlay over **main gameplay**. Positions come from the typed object map (tabs, panels, scroll lists, buy buttons), not live observation folders — except Troubleshoot, which also writes Observation evidence.

Overlay marks: **clicks show hotkeys**; **non-clicks show icons**. Press **D** to flip non-click marks to their hotkeys (and back). Flight deck shows a bold **D = …** line while LCO is on.

## Hotkeys (default)

| Key | Action | Overlay mark |
| --- | --- | --- |
| Q / W / E | Attack / Defense / Utility tab (no retap if already active) | Hotkey (click) |
| 1–6 | Buy on the visible 2×3 grid | Hotkey (click) |
| R / F | One card-row drag | ▲ / ▼ (or R / F after D) |
| T / G | Momentum fling toward list top / bottom | stacked ▲▲▲ / ▼▼▼ (or T / G after D) |
| V | Stat collect atom once | ★ (or V after D) |
| B | Redetect panel + buy grid (no scroll) | ↻ (or B after D) |
| D | Toggle non-click icons ↔ hotkeys | — |
| ` | Pause / resume LCO (gray inert marks; session stays) | — |
| Esc | Exit Live Control (and stop Observation if Troubleshoot owns it) |

Stay in mode after each fire. Pointer passes through. Cursor **stays** on the last click (no restore). Clicks use humanize **off** for precision.

## U → 1 vs U → 2

| | **U → 1 Enter Live Control** | **U → 2 Troubleshoot Live Control** |
| --- | --- | --- |
| Purpose | Day-to-day play | Diagnose scroll/buy misses |
| Observation | Must be off; refused if active | Starts `live-control-troubleshoot-<timestamp>` under `screen-maps/` |
| Evidence | None | Before/after frames + `live_control_action` timeline rows (params, snap, detector reason) |
| Exit | Hides overlay | Hides overlay **and** stops the Observation session |

Injected Live Control mouse is ignored by the Observation hook, so Troubleshoot pushes evidence from Live Control itself — not from mouse mirroring.

After a bad run: Esc, then point at the new `screen-maps/live-control-troubleshoot-…` folder (timeline + PNGs).

## Scroll / alignment

Upgrade lists are short **continuous** lists, not discrete pages. **R/F** move one calibrated row (same physics as Loops `list_scroll_*_1`), settle briefly, screenshot, and park 1–6 on whatever card rows are visible.

After enter / tab / **R/F** / **B**, Live Control **detects card rows** from the screenshot (edge energy). Playbook coords are fallback when detection finds nothing.

**Q/W/E** seek list top after the tab tap (game remembers per-tab scroll). **T** flings toward list top. **B** only re-reads the current frame (panel + buy slots) — hit it when markers look misaligned without changing scroll. **D** reveals which keys drive the icon marks. **`** pauses (gray / inert, typing passes through) without exiting; **`** again resumes; **Esc** exits.

Amber circles = geometry unsure (mid-scroll / odd gap). Buys still fire — amber is advisory only.

## Code

- `src/idle_lab/live_control/` — object map + playbook projection, overlay, controller  
- `ObservationController.note_live_control` — Troubleshoot evidence bridge  
- Flight-deck actions: `live_control_enter` / `live_control_enter_troubleshoot` / `live_control_exit` / `live_control_toggle`
