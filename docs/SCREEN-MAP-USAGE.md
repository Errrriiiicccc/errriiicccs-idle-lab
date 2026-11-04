# Screen Map — usage

Manual screenshot batches for mapping game screens. Same Idle Lab window as Clicker / Automations; uses the **same window anchor**.

## Setup

1. Launch Idle Lab (`pythonw -m idle_lab` from the venv).
2. Use the top **ANCHOR** bar: **Set anchor**, then click the emulator/game window.
3. Open the **Screen Map** tab.

## Capture a batch

1. Click **Start batch…** and enter a folder title (e.g. `tower-menus`).
2. A folder is created under `screen-maps/<batch-slug>/` (project root). Screenshot mode turns **ON**.
3. Navigate the game to a screen you care about.
4. Press **Space** → Idle Lab **captures immediately** (loading overlay: Capturing…), then a title dialog opens already focused → type a name → **Save** / Enter (Saving… overlay). Wait until status says Ready before the next Space.
5. Repeat for every important screen.
6. Press **Esc** (with no title dialog open) or click **End batch** to finish.

### Esc hierarchy

- Title dialog open → Esc **cancels the dialog only** (bitmap discarded, nothing saved).
- Otherwise in screenshot mode → Esc **ends the batch**.

### Responsiveness / focus

- While Capturing… or Saving…, a loading overlay covers the Screen Map tab and Space is ignored (no backlog of shots).
- Title dialogs stay topmost and use Win32 focus steal so you can type without clicking the field first. Space/Esc pass through to the dialog while it is open.

## Batch folder contents

```
screen-maps/<batch-slug>/
  01_main-hud.png
  02_workshop.png
  manifest.json
```

`manifest.json` holds batch metadata and one object per shot: `index`, `title`, `filename`, `captured_at`, optional `anchor` hints, plus null placeholders `classification`, `how_opened`, `notes` for a review chat to fill.

## Browse + screenshot viewer

- Left column lists every batch under `screen-maps/` (Refresh after captures outside this session).
- Select a batch → right column lists each captured screen. Click a row to open the viewer (←/→ to flip).
- **View all screenshots** opens the same viewer at the first shot.
- AI Batches can **Link Screen Map…** and jump here to inspect what was captured.

## After the batch

1. Optionally click **Open folder** (or browse `screen-maps/`).
2. New Cursor chat → paste [SCREEN-MAP-REVIEW-PROMPT.md](SCREEN-MAP-REVIEW-PROMPT.md) → point at the batch folder.
3. That chat classifies screens and asks how each was opened. Strategy / loops / CSV belong in a later deep-dive — not in this tab.

Workspace vision notes (outside this repo): `idle-lab/docs/POC/SCREEN-MAP-REVIEW-PROMPT.md`.

## Failures

- Missing / closed / minimized anchor → capture is **refused** with a status message (no silent empty file).
- Empty batch or shot titles are rejected.
