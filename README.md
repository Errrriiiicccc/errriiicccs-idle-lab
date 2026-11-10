# Errriiiccc's Idle Lab

Personal Windows **human-translation workbench**: show a screen, say what you want; AI helps author file-backed automations; Idle Lab runs them with ordinary input, pixels, and first-party exports when available. No process injection.

**Target UX:** **Flight Deck** (hotkeys) ↔ **Idle Lab** (mouse) — never both at once — opening the same **Labs** (LOL, Molecule Lab with Atom create, Observation Lab).  
**Code today** still ships the older mega-tab POC; the redesign is locked in docs and waiting on a shape-first build.

Check the target app’s rules before leaving a run going.

| Doc | Role |
| --- | --- |
| [docs/VISION.md](docs/VISION.md) | Purpose |
| [docs/pieces/README.md](docs/pieces/README.md) | Redesign map (shell + hygiene **agreed**) |
| [docs/FEATURES.md](docs/FEATURES.md) | Target shell vs ships today |
| [docs/CONTINUATION.md](docs/CONTINUATION.md) | Next chat focus |
| [AGENTS.md](AGENTS.md) | Agent entry |
| [archive/README.md](archive/README.md) | Deprecated attic (app never loads) |

## Run

```powershell
cd c:\DEV\Projects\Cursor\errriiicccs-idle-lab
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\pythonw.exe -m idle_lab
```

System deps for OCR/clips: [Tesseract](https://github.com/tesseract-ocr/tesseract) and `ffmpeg` on `PATH`.

## Today’s POC workspaces (until rebuild)

- **Bench** — presets / click logger → becomes **Atom Create** in Molecule Lab  
- **Observe** — sessions → **Observation Lab** (User)  
- **Missions** — AI batches → **Observation Lab** (AI mission)  
- **Loops** + composer → **Molecule Lab**  
- **Flight Deck** + **LCO** → redesigned Deck + **LOL**

Chrome: Anchor, Refresh (F5), Restart, Stop all / Deactivate. [docs/REFRESH-RESTART.md](docs/REFRESH-RESTART.md).

Operator how-tos (legacy names): [docs/USAGE.md](docs/USAGE.md), [docs/SMOKE-TESTS.md](docs/SMOKE-TESTS.md).  
Harness: [docs/HARNESS.md](docs/HARNESS.md).

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m idle_lab.harness story schema-validate-all
```

## Repo

https://github.com/Errrriiiicccc/errriiicccs-idle-lab

Push only outside Mon–Fri 09:00–17:00 Eastern unless overridden.

## Origin

Forked from `tower-autoclicker` (untouched). Pre-fork notes under workspace `idle-lab/docs/` are historical — purpose is [docs/VISION.md](docs/VISION.md) here.
