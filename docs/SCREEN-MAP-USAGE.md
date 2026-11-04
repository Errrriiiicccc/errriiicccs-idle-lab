# Screen Map — usage

Manual screenshot batches for mapping game screens. Same Idle Lab window as Clicker / Automations; uses the **same window anchor**.

## Setup

1. Launch Idle Lab (`pythonw -m idle_lab` from the venv).
2. On the **Clicker** tab: **Set anchor**, then click the emulator/game window.
3. Open the **Screen Map** tab.

## Capture a batch

1. Click **Start batch…** and enter a folder title (e.g. `tower-menus`).
2. A folder is created under `screen-maps/<batch-slug>/` (project root). Screenshot mode turns **ON**.
3. Navigate the game to a screen you care about.
4. Press **Space** → type a short title → **Capture** (or Enter). Idle Lab grabs the anchored window as PNG and appends a manifest row.
5. Repeat for every important screen.
6. Press **Esc** (with no title dialog open) or click **End batch** to finish.

### Esc hierarchy

- Title dialog open → Esc **cancels the dialog only** (no capture).
- Otherwise in screenshot mode → Esc **ends the batch**.

### Focus strategy (BlueStacks)

Title dialogs use the same pattern as other Idle Lab modals: transient window, brief topmost, `grab_set`, and focus on the entry. While the dialog is open, Space/Esc are **not** swallowed by the global hook so you can type spaces and cancel with Esc. When screenshot mode is on and no dialog is open, Space/Esc are swallowed so BlueStacks does not see them.

If the dialog does not appear focused, click it once and type — capture still uses the anchored window, not whichever window has focus.

## Batch folder contents

```
screen-maps/<batch-slug>/
  01_main-hud.png
  02_workshop.png
  manifest.json
```

`manifest.json` holds batch metadata and one object per shot: `index`, `title`, `filename`, `captured_at`, optional `anchor` hints, plus null placeholders `classification`, `how_opened`, `notes` for a review chat to fill.

## After the batch

1. Optionally click **Open folder** (or browse `screen-maps/`).
2. New Cursor chat → paste [SCREEN-MAP-REVIEW-PROMPT.md](SCREEN-MAP-REVIEW-PROMPT.md) → point at the batch folder.
3. That chat classifies screens and asks how each was opened. Strategy / loops / CSV belong in a later deep-dive — not in this tab.

Workspace vision notes (outside this repo): `idle-lab/docs/POC/SCREEN-MAP-REVIEW-PROMPT.md`.

## Failures

- Missing / closed / minimized anchor → capture is **refused** with a status message (no silent empty file).
- Empty batch or shot titles are rejected.
