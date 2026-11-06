# L7 — Humanize & input quality

**Status:** deep-dive complete (2026-11-05)  
**Pieces / composites:** P2, C3  
**Split:** balanced (feel + timing math)

## 1. Restatement

Humanize (Off/Light/Medium/Heavy) applies runtime aim jitter, delay/hold variance, and eased cursor travel — **not** stored in preset JSON, **not** marketed as anti-detect. Goal: less robotic pacing and slightly forgiving aim for attended/personal use, including future assistive scenarios. Quality = **predictable levels**, visible motion optional, never silent wrong-target clicks.

## 2. Analogues studied

| Analogue | Why |
| --- | --- |
| CNC feed rate / CAM | Speed vs precision tradeoff as a named knob |
| Macro tools (AHK, etc.) | MouseSpeed / delays as user-facing settings |
| Windows Voice Access | Move faster/slower, Stop, grid overlays, waits in shortcuts |
| Ableton “toolless” motion | Direct, continuous control feel |

## 3. Extracts

### CAM / feed rate metaphor

- Operators pick **feed** knowing finish quality and cycle time trade off.
- Dry-run / single-block execution before committing a long toolpath.
- Maps cleanly: Humanize level = feed; presets = toolpath; anchor = work coordinate system.

### Voice Access pacing & overlays

- Continuous move with **faster/slower** and hard **Stop**.
- **Grid / number overlays** make the next target legible before actuation.
- Shortcuts allow **explicit wait** steps between mouse/key actions (sequence hygiene).
- Mark → drag is a two-phase gesture with visible state.

Sources: [Use the mouse with voice](https://support.microsoft.com/en-us/accessibility/windows/voice-access/use-the-mouse-with-voice), [Voice access command list](https://support.microsoft.com/en-us/accessibility/windows/voice-access/voice-access-command-list), [Voice shortcuts](https://support.microsoft.com/en-us/accessibility/windows/voice-access/use-voice-to-create-voice-access-shortcuts).

## 4. Idle Lab translation

| Borrow | Product meaning |
| --- | --- |
| Named feed levels | Keep Off→Heavy; document **what each changes** (px jitter, % delay, travel steps) in UI tooltip |
| Stop always wins | Transport Stop all interrupts mid-travel (engine must check cancel between easing steps) |
| Show next target | Optional overlay dot / ghost cursor before click (assistive + debug); off by default for speed |
| Wait in sequences | Already have `wait` action; humanize should not replace explicit waits |
| Dry-run path | “Preview preset” without clicking (move overlay only) |
| Background vs foreground | Background skips travel — document that Heavy is mostly a foreground concept |

**Ethics / framing:** Humanize = comfort + robustness for noisy coordinates; **not** evasion. Keep README honest.

## 5. Conflict check

- Heavy travel time extends scheduler critical sections (L3) — levels must have rough **duration budgets**.
- Writing jitter into preset JSON would break AI determinism / prompt packets — keep runtime-only.
- Assistive users may want **slower and more visible**, not more random — consider splitting “pace” vs “noise” later.

## 6. Candidate experiments

1. UI tooltips: numeric summary per level from `humanize.py` constants.
2. Cancel check inside cursor travel loop.
3. Optional “show aim” debug: draw target before down/up.
4. Profile: Medium vs Off mean tick duration on `humanize_upgrade_loop`.

## 7. Takeaways

Treat Humanize as a **feed-rate + optional visibility** control. Steal Stop/pacing clarity from Voice Access; keep anti-detect claims out.
