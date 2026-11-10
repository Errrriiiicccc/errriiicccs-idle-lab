# Shell

**Job:** Two exclusive surfaces — **Idle Lab** (mouse, no hotkeys) and **Flight Deck** (hotkeys, lightweight Labs) — never shown at once.  
**Decisions:** [decisions.md](decisions.md)

## Hard rules (settled)

1. **Never** show Flight Deck and Idle Lab at the same time.
2. **Idle Lab open** → **no** keyboard hotkeys (buttons only).
3. **Anything running** → Idle Lab closed; **Flight Deck only**.
4. `` ` `` = Activate / Deactivate on Flight Deck; resume handle after Deactivate (continue / restart-wipe / Esc → Idle Lab).
5. Factory / fresh start → Idle Lab on **Info**. Thereafter persist **last selected tab**.
6. Live status lives in Idle Lab **chrome** (header or bottom bar) — not inside Info.

## Surfaces

| Surface | Role |
| --- | --- |
| **Idle Lab** | Mouse home. Tabs = **Info** + Labs. Shared wrap: Anchor, Restart, Settings, tab switch, live status strip. |
| **Flight Deck** | Hotkey companion when Deck is the surface (idle-on-deck or something running). Lightweight Lab windows + atom-create overlay chords. |

## Tabs inventory

| Tab | Doc |
| --- | --- |
| **Info** | [info.md](info.md) |
| **Live Overlay Lab (LOL)** | [lol.md](lol.md) |
| **Molecule Lab** | [molecule-lab.md](molecule-lab.md) — Atom + Molecule; Trial cohesion parked |
| **Observation Lab** | [observation-lab.md](observation-lab.md) — User + AI mission |
| **Flight Deck** | [flight-deck.md](flight-deck.md) — dive complete enough; soft leftovers parked |

~~Autoclicker Lab~~ → Molecule Lab Atom ([autoclicker-lab.md](autoclicker-lab.md)).
