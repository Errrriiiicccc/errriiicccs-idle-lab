# L10 — Assistive attended sessions

**Status:** deep-dive complete (2026-11-05)  
**Pieces / composites:** P12, C9 (uses P1, P2, P10; ethics overlay on all lanes)  
**Split:** primarily UX / safety; engine for cancel & preview

## 1. Restatement

Horizon: Idle Lab as a **general Windows GUI observation + actuation lab** that can help people who need repeatable GUI assistance — not stealth gaming. Assistive use demands **attended** operation: clear what will happen next, easy Stop, no hostile timers, minimal scanning cost, reversible mistakes. Personal product now; these principles also raise quality for Eric’s own operation.

## 2. Analogues studied

| Analogue | Why |
| --- | --- |
| Switch access / scanning UIs | Every control is expensive; Stop & grouping matter |
| Windows Voice Access | Overlays, Stop, waits, visible mark/drag |
| Attended RPA / SCADA Manual | Human authority; confirm consequential acts |
| NARBE / one-switch game hubs | Pause everywhere; large targets; independence |

## 3. Extracts

### Switch access & scanning

- Auto-scan advances on a timer; step-scan uses one switch to move, one to select — **10–30s per action** is normal.
- Design: short logical focus order, **group to skip**, large targets, **no undefeated timeouts**, undo/back, persist partial work.
- Tiny toolbar grids exhaust users; roving tabindex / grouped regions help.

Sources: [AccessKit switch control](https://accesskit.mabit.ca/en/percepta/switch-control), [Tamil DS switch scanning](https://www.tamilui.com/accessibility/switch-control-scanning), [Arizona AT guide](https://accessibility.arizona.edu/index%2Ephp/tools-checklists/assistive-technology-guide), [W3C clear control–content relationship](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o1p06-control-actions/).

### Voice Access

- Grid/number overlays = **show where actuation will land**.
- Continuous move needs **Stop**; shortcuts include explicit waits.
- Window-scoped overlays (“here”) beat full-desktop chaos — maps to **anchor**.

### One-switch independence (NARBE)

- Pause reachable from anywhere; on-screen Pause pairs with hold gesture.
- High contrast, large hit targets (≥64px guidance in their hub), never color-alone state.

Source: [NARBE developer guide](https://narbehouse.github.io/developer-guide.html).

## 4. Idle Lab translation

| Principle | Shell / UX | Engine |
| --- | --- | --- |
| Big Stop | Stop all always visible (L1); high contrast | Immediate cooperative cancel between actions & humanize steps |
| Attended default | Mode: Supervised (confirm first click of session / of event) vs Auto | Optional confirm gate |
| Show next action | Overlay ghost target + plain-language next step | Player publishes next `nx,ny` + description |
| No hostile timers | Don’t auto-dismiss confirmations; extendable countdowns | Countdown cancelable |
| Grouped IA | Workspaces reduce simultaneous controls (Bench vs Loops) | — |
| Undo / safe abort | Restart vs Stop distinguished (Ableton double-stop lesson) | Clear semantics in docs |
| Transparency | Console + trace (L4) explain what fired | No silent background surprises without indicator |
| Anchor as “here” | Cyan frame = Voice Access “grid here” | Refuse act if unanchored |

**Non-goals for assistive claim:** hiding from OS accessibility APIs, forcing use without consent on shared PCs, replacing dedicated AT (Narrator, Voice Access) — Idle Lab **complements** by automating brittle GUIs those tools struggle with.

## 5. Conflict check

- Full Auto unattended game farming **conflicts** with assistive ethics messaging — keep product voice honest; modes make intent explicit.
- Dense CustomTkinter chrome can violate “few scanning stops” — redesign should **reduce** always-visible buttons (L1 transport + workspace content).
- Humanize randomness (L7) can confuse AT users — offer “pace without noise”.

## 6. Candidate experiments

1. Supervised mode spike: before first actuation after Start, show “Next: click Health (nx,ny)” + Confirm / Cancel.  
2. Ensure Stop all cancels humanize mid-travel (shared with L7).  
3. Accessibility pass on redesign canvas: contrast, target size, Stop placement.  
4. Document “Attended assistive session” recipe: anchor → Supervised → one collection → Stop.

## 7. Takeaways

Assistive readiness is mostly **operator control + visibility + cancel**, not a separate product line. Steal scanning economics and Stop discipline from switch access; steal overlays from Voice Access; keep Auto as an explicit mode, not the only story.
