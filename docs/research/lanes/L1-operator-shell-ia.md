# L1 — Operator shell IA

**Status:** deep-dive complete (2026-11-05)  
**Pieces / composites:** P10, C7 (also touches P5/P6 for live status)  
**Split:** primarily UX / IA; light engine implication (what state the shell must expose)

## 1. Restatement (Idle Lab vocabulary)

The shell is the **operator console**: how a human starts, stops, reloads, and switches workspaces (**Bench · Observe · Missions · Loops**; older prose said Clicker / Automations / Screen Map / AI Batches) while seeing whether automation is idle, running, deferred, or disagreeing with intent. Transport language (Refresh / Restart / Stop all) must be unmistakable and always reachable.

## 2. Analogues studied

| Analogue | Why |
| --- | --- |
| Ableton Live Control Bar | Persistent transport; Session vs Arrangement as workspaces |
| SCADA / HMI faceplates + modes | Manual / Auto / Off; commanded vs actual; confirm consequential actions |
| NRC / HSI automation guidance | Modes vs levels of automation; mode confusion risks |
| Blender / DAW workspace configs | Task-specific layouts without leaving one window |

## 3. Extracts

### Ableton Live (Control Bar)

- **Mental model:** One persistent control bar owns play/stop/record; views (Session vs Arrangement) change *what you edit*, not *whether the set is running*.
- **State:** Play vs stop is global; Follow is display-only and must not be confused with playback source.
- **Failure feedback:** Separate “Back to Arrangement” style indicators when Session overrides Arrangement — status that explains *why* sound/behavior differs from expectation.
- **Authoring:** Direct manipulation of clips; transport is not buried in menus.
- **Constraints:** Space toggles play/stop; double-stop returns to start — cheap, muscle-memory actions.

Sources: [Ableton Live Concepts — Control Bar](https://www.ableton.com/en/manual/live-concepts/), [Transport / Follow tutorial](https://good-looking-out.github.io/tutorials/ableton-live/working-with-views-tracks-projects-and-content/how-to-use-the-transport-bar-and-follow-behavior/).

### SCADA / HMI faceplates

- **Mental model:** Overview shows situation; **faceplate** is where you act on one device. Mode layers are shown separately (physical HOA ≠ controller Auto/Manual ≠ local/remote).
- **State:** Commanded vs feedback; **disagreement** is the primary diagnostic.
- **Failure:** Gray unavailable commands and name the interlock/permissive holding the device — never a silent no-op button.
- **Authoring:** Faceplates are logic-free; controller owns behavior (maps to files-as-truth: UI should not invent automation semantics).
- **Safety:** Confirm Start/Stop/mode change; preserve limits even in Manual.

Sources: [Curry Controls — HMI Faceplates](https://www.currycontrols.com/controls/scada-hmi/hmi-design/faceplates/), [Rockwell Process HMI Style Guide](https://literature.rockwellautomation.com/idc/groups/literature/documents/wp/proces-wp023_-en-p.pdf), [ACORN HSI Style Guide](https://doi.org/10.2172/2279051).

### Modes of automation (NRC HSI)

- Modes are **mutually exclusive behavior sets**, not “how smart” the system is.
- Mode confusion is a known failure mode: operator believes Manual while Auto is still driving (or the reverse).

Source: [NUREG/CR-7126 Human-System Interfaces to Automatic Systems](https://www.nrc.gov/docs/ML1027/ML102720251.pdf).

## 4. Idle Lab translation

| Borrow | UI | Engine |
| --- | --- | --- |
| Persistent transport strip | Always-visible Refresh / Restart / Stop all; workspace switcher adjacent, not nested | Stop all must hard-abort Clicker + Automations + AI Batch runners |
| Mode as first-class | Show **Attended / Auto running / Stopped** (names TBD) with text+icon, not color alone | Runtime publishes a single `operator_mode` / run phase |
| Commanded vs actual | “Wanted: Automations Start” vs “Worker: recording clip (blocking)” | Queue UI already has running/waiting/deferred — promote disagreement (due but deferred) |
| Faceplate pattern | Selecting an event/collection opens a consistent detail “faceplate” (Basic/Detailed) | Keep logic in JSON; UI renders |
| Workspace ≠ transport | Bench/Observe/Missions/Loops change chrome; transport stays put | No |

## 5. Conflict check

- **Files-as-truth:** Shell must not become a second source of automation logic (SCADA lesson: faceplate has no logic).
- **Single-worker scheduler:** Transport must expose *blocking* honestly (clip recording) or operators will think Stop failed.
- **Redesign lock:** Transport + mode strip is the safe shared surface; deep tab restyles can wait. Avoid packing stats/schedules into the first viewport of each workspace.

## 6. Candidate experiments (reversible)

1. Prototype a **always-on transport strip** on the redesign canvas only (no engine change): labels Refresh / Restart / Stop all + mode chip.
2. Add a **disagreement line** in Automations queue: “due but deferred because `<event>` running”.
3. Document mode glossary in shell copy: Stopped / Running / Recording-blocked / Anchored vs unanchored.

## 7. Takeaways for redesign chat

- Prefer **one window, persistent transport**, Ableton-style.
- Prefer **explicit modes** and **commanded vs actual**, SCADA-style.
- Workspaces are layouts/tasks; they must not hide Stop.
