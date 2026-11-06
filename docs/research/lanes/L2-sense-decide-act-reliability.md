# L2 — Sense–decide–act reliability

**Status:** deep-dive complete (2026-11-05)  
**Pieces / composites:** P3, P4, C1 (also `ensure_*` / `detect_*` helpers)  
**Split:** primarily engine; UX for failure evidence

## 1. Restatement

Closed-loop ticks fail when perception is stale, OCR is noisy, or actions fire before the UI is ready. Idle Lab already has `ensure_upgrade_tab`, `detect_panel`, `seek_list_top` — this lane defines the **reliability grammar**: wait for observable readiness, retry with evidence, deadband noisy values, never silent force-click.

## 2. Analogues studied

| Analogue | Why |
| --- | --- |
| Playwright auto-waiting / actionability | Wait for ready state instead of `sleep` |
| SikuliX / OculiX vision verbs | `wait` / `exists` / save last screen on fail |
| PID / control deadband | Don’t act on noise in OCR numbers |
| Existing Idle Lab `ensure_*` | Local proof that observe-before-click works |

## 3. Extracts

### Playwright actionability

Before click/fill, auto-checks: unique locator, **visible**, **stable** (not animating), **receives events**, **enabled**. Retries until action timeout. Prefer web-first assertions (`expect(…).toBeVisible()`) over hard `waitForTimeout`. For hydration-style races with no signal: `expect(…).toPass()` retries a whole act+assert block.

Sources: [Auto-waiting](https://playwright.dev/docs/actionability), [Best practices](https://playwright.dev/docs/best-practices), [Timeouts](https://playwright.dev/docs/test-timeouts), [Checkly waits guide](https://www.checklyhq.com/docs/learn/playwright/waits-and-timeouts/).

### SikuliX / OculiX

Verbs: `find` / `exists` / `wait` / `waitVanish` / `findAll`. `AutoWaitTimeout` makes click implicitly wait. On failure: `saveLastScreenImage()`, tight crops, restrict `Region`, similarity ≥ ~0.8–0.9 for templates. OCR: log `region.text()`, scale so capital height ~30px; don’t trust OCR alone for icons.

Sources: [OculiX visual matching](https://oculix.org/guides/visual-matching/), [SikuliX FindFailed Q&A](https://answers.launchpad.net/sikuli/+question/670724), [OculiX text/OCR](https://docs.oculix.org/textandocr/).

### PID deadband (conceptual)

Act only when measured value crosses a band around the last acted value — reduces chatter from OCR flipping `12.4B` ↔ `12.5B` or transient misreads.

## 4. Idle Lab translation

| Borrow | Engine | UI |
| --- | --- | --- |
| Actionability checklist | Before `click`/`play_preset`: optional **ready predicates** (panel_open, OCR match, template present, ROI stable N frames) | Console shows which check failed |
| Auto-wait vs hard wait | Prefer `wait_until` action over fixed `wait` ms when sensing | Basic description: “wait until SIGNAL is A” |
| Observation vs inference | Keep `variable_raw` + `variable`; add confidence / parse_ok | Show raw when decide fails |
| Deadband | For currency/wave: `changed_by` / `min_delta` before buy/branch | — |
| Failure dump | On OCR/decide/act fail: save crop + full window shot + intended action | One-click open last failure evidence |
| `force` | Explicit `force: true` to skip readiness (like Playwright) — default off | Warn in Detailed view |

## 5. Conflict check

- **Single-worker:** Long auto-waits block the scheduler (same as clip recording). Cap wait budgets; high-priority events still need a story for “I’m waiting”.
- **Files-as-truth:** Readiness should be declarative in JSON (`until`, `timeout_ms`, `on_timeout`) not hidden Python.
- **Redesign:** Don’t block shell work on this; reliability is engine + console copy.

## 6. Candidate experiments

1. Schema spike: `wait_until` action `{ "variable"|"roi_presence"|"panel", "equals", "timeout_ms" }`.
2. On OCR parse fail: always write `runs/failures/<ts>_roi.png` + console path.
3. Currency deadband on one endgame ROI event; compare CSV chatter before/after.
4. Wrap `ensure_upgrade_tab` pattern as documented **readiness idiom** in automation-schema.md.

## 7. Takeaways

Hard sleeps are a smell. Idle Lab should grow **observable readiness** + **evidence on fail**, matching Playwright/Sikuli, while keeping wait budgets visible to the priority scheduler.
