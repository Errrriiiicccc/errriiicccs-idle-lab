# The Tower — navigation playbook (for event collections)

One-stop reference for Automations **events/collections**.  
Workflow: Idle Lab **AI Batches** + **Screen Map**.

**Canonical scroll lab:** `ai-batches/upgrade-scroll-controlled/`  
**Screen Map:** `screen-maps/ai-run-upgrade-scroll-controlled/`  
**Prior (do not re-use for calibration):** wheel batches (`upgrade-scroll-calibrate`, early menu-nav labs)

---

## How to gather

1. ANCHOR → BlueStacks (`64x Android`).
2. Restart Idle Lab after runner code changes.
3. AI Batches → Reload → run the active batch → tell the AI chat when idle.

### Hard rules

| Rule | Detail |
| --- | --- |
| Observe before acting | Status/screenshot first; `ensure_upgrade_tab` skips click if already open. |
| Never retap active tab | Closes the panel. |
| Upgrade lists = **drag**, not wheel | Wheel flings (Attack jumped to Multishot in one notch). |
| Partial drag + hold | `drag_fraction≈0.10`, `hold_end_ms≈450` before release. |
| Status after every drag | Settle → status shot → (optional settle confirm) → ROI decide. |
| Stop on unchanged ROI | `mean_abs_diff < ~0.015` ⇒ at top/bottom. |

---

## Confirmed findings

### Currency HUD

- Tap cluster `nx≈0.15, ny≈0.09`: cash+coins **balances ↔ /min**; gems stay stock.
- OCR must know mode or force balances before reading.
- Tuned ROIs (593×1028 lab window, top-left stack): cash `ny≈0.048`, coins `ny≈0.082`, diamonds `ny≈0.120`. Wave label is mid-right just above upgrades (`nx≈0.52, ny≈0.555`), not top chrome.

### Upgrade tabs

| Tab | Approx click | Detect (tile-body RGB) |
| --- | --- | --- |
| Attack | `0.20, 0.955` | cyan/blue |
| Defense | `0.40, 0.955` | red/pink |
| Utility | `0.60, 0.955` | yellow |
| UW | `~0.80, 0.955` | (not calibrated) |

`ensure_upgrade_tab` used this successfully (skip when already on target; switch when not).

**Probe miss (2026-11-06):** seed used Defense `nx=0.50` / Utility `nx=0.80` → Defense tap opened **Utility**; `0.80` is UW. Always use the table above (or omit `nx` and take runner defaults).

**Currency toggle probe:** one tap `0.15, 0.09` flipped cash+coins balances → `/min`; gems stayed stock.

**Buy rule:** always `seek_top_first` (or equivalent) before Damage/Health taps at `0.38, 0.735`. Mid-list open → wrong card (confirmed `damage-buy-calibrate` + Eric note).

**scroll_map:** `max_steps: 0` is seek-only (runner must not coerce 0 → 12).

**Loops atoms:** prefer shared `scroll_list` / `list_scroll_down_1` / `list_scroll_up_1` (tab-agnostic) over duplicating drag params per Attack/Defense/Utility molecule.

### First-row buy taps (Damage / Health)

Calibrated from `ai-run-upgrade-scroll-controlled` Attack/Defense **top** shots (593×1028 lab window):

| Upgrade | Tab | Buy click (normalized) | Notes |
| --- | --- | --- | --- |
| Damage | Attack | `0.38, 0.735` | Left card body / value·cost. Card ≈ `ny 0.67–0.82`. Reconfirmed after seek-top (`damage-buy-calibrate` iter 002). |
| Health | Defense | `0.38, 0.735` | Same grid slot when Defense is open. Reconfirmed after seek-top (same run). |

**Miss to avoid:** `ny≈0.635` lands on the **ATTACK/DEFENSE UPGRADES** header (just above the card) — that was the humanize-loop miss.

Verify batch: `ai-batches/damage-buy-calibrate/` (before/after cash + value).

### Controlled scroll calibration (`upgrade-scroll-controlled`)

**Params that worked:** `method: drag`, `drag_fraction: 0.10`, `hold_end_ms: 450`, `settle_ms: 800`, `settle_confirm_ms: 400`, `unchanged_threshold: 0.015`.

| Tab | Seek-up to top | Downs until bottom | Typical move `mean_abs_diff` | Stop diff |
| --- | --- | --- | --- | --- |
| Attack | 1 (already top) | **5 moves + 1 stop** (6 applied) | ~0.11–0.12 | ~0.004 |
| Defense | 1 (already top) | **3 moves + 1 stop** | ~0.11–0.12 | ~0.004 |
| Utility | 1 (already top) | **2 moves + 1 stop** | ~0.11–0.13 | ~0.005 |

**Partial coverage confirmed:** one `0.10` drag advances ~**one tile row** (Attack top Damage… → after down-01 Crit/Range/Damage·Meter + Multishot peeking — not a fling to Bounce Shot). Reconfirmed 2026-11-06 `probe-scroll-one-row` iter 003 (`mean_abs_diff≈0.135`).

**List endpoints (this account):**

- **Attack top:** Damage, Attack Speed, Crit Chance/Factor, Range, Damage/Meter  
- **Attack bottom:** Rapid Fire…, Bounce Shot Chance/Targets/Range  
- **Defense top:** Health, Health Regen, Defense %, Defense Absolute, Thorn, Lifesteal  
- **Defense mid/bottom:** Knockback Chance/Force, Orb Speed, Orbs (from earlier labs + controlled downs)  
- **Utility top:** Cash Bonus, Cash/Wave, Coins/Kill, Coins/Wave, Free Attack/Defense Upgrade  
- **Utility lower:** Free Utility Upgrade, Interest/Wave, … (2 downs to bottom on this account)

**Collections estimate:** to move ~N rows, use ~N controlled `0.10` drags (not wheel notches). Always status-check; don’t assume count alone.

### Failed approaches (historical)

- Blind fixed wheel counts → closed Attack / scrolled past bottom.  
- Neighbor “safe open” → left already-open Attack.  
- Wheel `scroll_map` → fling; Attack 13 “downs” while already near bottom.

### Other UI

- Mid HUD + speed `x3.5`. Cart / hamburger / in-battle rail + EXIT BATTLE — avoid while scrolling.

---

## For collections

1. `ensure_upgrade_tab` for Attack/Defense/Utility.  
2. If scroll position unknown: seek top with same drag (up until unchanged).  
3. Controlled partial drags until tile visible; status after each.  
4. Tap tile.  
5. Prefer linked Screen Map `ai-run-upgrade-scroll-controlled` over re-exploring.
