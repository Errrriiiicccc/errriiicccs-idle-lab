# Review prompt — paste after a Screen Map batch

Use this in a **new chat** (Agent or Plan) once a batch folder exists. Attach or point at the batch directory (images + `manifest.json`). Goal: classify screens and gather navigation details for the Idle Lab screen map — not to write automation code unless asked.

---

## Role

You are helping Eric build a **screen map** for idle-game automation (first game: The Tower on BlueStacks). He captured a batch of anchored window screenshots with titles. You will review them, classify them, and ask focused questions so we can later define loops, phases, ROIs, and CSV fields in the vision/deep-dive chat.

## Inputs

Eric will give you:

- Path to a batch folder under the Idle Lab repo (e.g. `screen-maps/<batch>/`)
- PNGs + `manifest.json` (titles, filenames, timestamps)

Read every image you can. Use titles as hints; trust pixels over filenames when they disagree.

## What to produce

Write (or update) a markdown screen-map draft Eric can keep — prefer saving under the batch folder or `idle-lab/docs/screen-maps/<batch>-map.md` if he asks you to write files.

For **each** screenshot:

1. **Id / title** (from manifest)
2. **Classification** — pick one primary, note secondary if needed:
   - `hud_run` — main run screen
   - `menu` — settings / tabs / workshop / lab / cards / events / etc.
   - `modal` — popup, reward claim, confirm
   - `end_of_run` — death / results / continue
   - `shop` / `upgrade` / `prestige` / `other` (say what)
3. **Visible data** — list readable numbers/labels that matter for automation or stats (wave, coins, gems, upgrade names/levels, timers, badges). Mark uncertain OCR guesses as uncertain if you are reading from the image.
4. **Likely purpose** — one sentence: why a human opens this screen.
5. **Open questions for Eric** — especially:
   - How did you open this screen (from where, what tap/button)?
   - What leaves this screen?
   - Is this reachable mid-run, only between runs, or both?
   - Any timed/limited element?
6. **Automation relevance** — `read` / `click` / `both` / `ignore_for_now`

Also produce a short **nav sketch**: bullet list of “From A → tap X → B” only where Eric confirmed or where the UI makes it obvious (label guesses clearly).

## How to work with Eric

- Batch questions; do not ask 40 one-liners. Group by screen or by “navigation,” “stats,” “ignore.”
- If two shots are the same screen, say so and merge.
- If a title is wrong/vague, propose a better canonical name.
- Do **not** invent full buy-priority strategies here.
- Do **not** require implementing Idle Lab code unless Eric asks.
- Unknowns are fine — list them under **Unknown / later**.

## Deliverable checklist

- [ ] Per-screen classifications filled
- [ ] Questions asked and answers captured into the map doc
- [ ] Draft list of candidate **CSV/stat fields** spotted on screens (name + which screen)
- [ ] Draft list of candidate **sequences** (human procedures) implied by navigation — names only
- [ ] Note what is still missing (screens not photographed yet)

## After this review

Eric returns to the Idle Lab vision/deep-dive chat (or a mapping chat) to turn this into loops, phases, ROI files, and automation collections. Your job ends at a solid classified map + answered navigation questions.
