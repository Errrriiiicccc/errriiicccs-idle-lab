# Live Control Overlay

**Status:** v1 + object map 2026-11-08  
**Enter:** flight deck **U → 1** (play) or **U → 2** (troubleshoot)  
**Exit:** Esc (deck shows Exit LCO while active; Activate/Deactivate blocked until LCO exits)  
**Object map:** [`automations/maps/tower_main_gameplay.objects.json`](../automations/maps/tower_main_gameplay.objects.json)  
**Detail:** [OBJECT-MAP.md](OBJECT-MAP.md)

Keyboard-driven overlay over **main gameplay**. Positions come from the typed object map (tabs, panels, scroll lists, buy buttons), not live observation folders — except Troubleshoot, which also writes Observation evidence.

Overlay marks: **clicks show hotkeys**; **non-clicks show icons**. **Hold D** to flip icons to hotkeys and paint HV diagram descriptors (group labels for tabs / buys / scroll; singleton stems for V and B). Flight deck shows a bold **HOLD D = DESCRIBE** line while LCO is on.

## Hotkeys (default)

| Key | Action | Overlay mark |
| --- | --- | --- |
| Q / W / E | Attack / Defense / Utility tab (no retap if already active) | Hotkey (click) |
| 1–6 | Buy on the visible 2×3 grid (label from catalog when identity known) | Hotkey (click) |
| R / F | One card-row drag | ▲ / ▼ (R / F while holding D) |
| T / G | Momentum fling toward list top / bottom | stacked ▲▲▲ / ▼▼▼ (T / G while holding D) |
| V | Stat collect atom once | clipboard (V while holding D) |
| C | Claim diamonds (timed tile; fine if absent) | ◆ (C while holding D) |
| B | Redetect panel + buy grid (no scroll) | ↻ (B while holding D) |
| A | Routine pack: Health → Damage → Claim (left rail) | ▸▸ (A while holding D) |
| D | Hold: icons → hotkeys + HV descriptors | — |
| ` | Pause / resume LCO (gray inert marks; session stays) | — |
| Esc | Exit Live Control (and stop Observation if Troubleshoot owns it) |

Stay in mode after each fire. Pointer passes through. Cursor **stays** on the last click (no restore). Clicks use humanize **off** for precision.

**Fire modes**

| Mode | Keys | Hold / repeat |
| --- | --- | --- |
| **Spam** | 1–6 buys, R/F scroll, T/G fling, C claim | Re-fires while the key is held; release stops |
| **Single** | Q/W/E tabs, V stat, B refresh | Fires once on key-down; hold does nothing extra |
| **Toggle** | A routine (Health → Damage → Claim) | Key-down arms a repeating loop (release ignored); press again to disarm. Esc / `` ` `` also clear it |

**Queue + focus colors:** keys pressed while an action is in flight enqueue FIFO and run in press order. During activity, marks use focus colors — **green** = current action; **armed toggle** = green outline with fill pulsing between active green and the mark’s resting color (not gray); **orange + N** = queued (1, 2, …; current/toggle marks have no number); **gray** = idle while something else is busy. Remaining steps inside a running routine count as queued too.

Scroll gesture settle after R/F/T/G (and tab-home fling) stays short (~80ms). Before buy-grid detect, LCO waits up to `detect_settle_ms` (~220ms) so 1–6 park on settled cards — not mid-fling frames. Pressing **A** again (or **`**) aborts the in-flight pack immediately; the hotkey drain stays free so orange queue marks + numbers can paint while work runs.

Describe (**D**) stays hold-to-show. **`** / **Esc** abort in-flight work immediately (mid-drag / queued repeats) — pause or exit still follows.

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

**Q/W/E** fling toward list top after the tab tap (game remembers per-tab scroll; same physics as **T**). **T** also flings toward list top. **B** only re-reads the current frame (panel + buy slots) — hit it when markers look misaligned without changing scroll. **A** runs the left-rail routine pack (Health → Damage → Claim; same atom as flight deck **A → 5**). **Hold D** describes related marks with HV connector lines and label rectangles (and flips icons to their keys). **`** pauses (gray / inert, typing passes through) without exiting; **`** again resumes; **Esc** exits.

Amber circles = geometry unsure (mid-scroll / odd gap). Buys still fire — amber is advisory only.

**Buy identity:** after detect, LCO OCRs each nameplate and scores every catalog *offset* (neighbor structure: Thorn beside Lifesteal implies Knockback below). Hold **D** shows `N:Label` (high conf), `N:Label~` (medium), `N:Label?` / `N:?` (low/unknown). Evidence carries `slot_confidence` / `offset_scores`. Tab home / **T** may fall back to page-1 only if OCR+structure miss. R/F use `drag_fraction≈0.10` + `hold_end_ms≈450`.

## Console (session log)

Flight deck **U → 3** toggles a persisted console preference (`settings.json` → `lco_console_enabled`). The resizable **LCO Console** window opens when Live Control starts (U → 1 / U → 2) and closes when LCO exits. **U → 4** cycles verbosity while the preference is on:

| Level | What gets logged |
| --- | --- |
| `events` | Key/action pressed |
| `results` | + one-line outcome (buy label, identity summary, scroll slot count, …) |
| `process` | + live steps (OCR prep scores, detect reasons, …) |

The window shows the live buffer, a **Copy** button, a display-only **Timestamps** toggle, and a `User Comment:` field + **Send** (Enter also sends). Comments are written as `User Comment: …` with timestamps. Timestamps always land in `console.log` even when the window hides them.

Each LCO enter with console on creates `runs/lco-console-<timestamp>/`. The buffer flushes to `console.log` on **pause** and **exit** (and on verbosity/toggle changes).

## From automations

Atoms can fire the same actions headlessly with the `lco` action type — `{ "type": "lco", "key": "W" }`, `{ "type": "lco", "action": "buy_3", "times": 5 }`. No overlay is drawn; detection, object map and scroll physics are shared with U → 1. See [automation-schema.md](automation-schema.md).

## Code

- `src/idle_lab/live_control/` — object map + playbook projection, overlay, controller (`run_action` + `NullOverlay` for headless use)  
- `AutomationRuntime._action_lco` — `lco` atom step → headless controller  
- `ObservationController.note_live_control` — Troubleshoot evidence bridge  
- Flight-deck actions: `live_control_enter` / `live_control_enter_troubleshoot` / `live_control_exit` / `live_control_toggle` / `live_control_console_toggle` / `live_control_console_verbosity`
