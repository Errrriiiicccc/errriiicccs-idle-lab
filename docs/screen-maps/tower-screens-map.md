# The Tower — Screen Map Draft

**Source batches:** `screen-maps/tower-screens`, `tower-screens-cont`, `tower-screens-cont-2`, `gem-screen`  
**Captured:** 2026-11-04 · emulator `64x Android`  
**Status:** navigation answers + gem claim priority folded in. Paths marked **confirmed**, **obvious**, **ignore_for_now**, or **more_info_needed**.

This doc is for later event / branch design. It is not a buy-priority strategy.

---

## HIGH PRIORITY — gem claim (opportunistic)

Timed gem offer pops on `hud_run` about every **10–15 minutes**. **Always claim when present.**

| | |
|---|---|
| **Id** | `hud_gem_claim` |
| **Shot** | [`gem-screen/01_gem-claim.png`](../../screen-maps/gem-screen/01_gem-claim.png) |
| **Position** | **Bottom-left** of the combat/HUD area — above the left mid-stat / HP panel, left of the speed control; floats over the run UI |
| **Look** | Neon-bordered tile: pink gem icon + count (e.g. `6`) + **CLAIM** |
| **Cadence** | ~every 10–15 min (**confirmed**) |
| **Automation** | **High priority.** On any click sequence while on (or returning to) the run HUD, include a **just-in-case tap** on this bottom-left claim spot even if the popup may not be visible — cheap insurance when it is. Prefer claiming before continuing other HUD clicks if presence can be detected. |
| **Relevance** | `click` (primary); OCR gem count optional |

Do **not** bury this under ignore lists. It outranks routine upgrade taps when the tile is up.

---

## Screen inventory (merged)

| Canonical id | Classification | Shots | Notes |
|---|---|---|---|
| `hud_run` | hud_run | tower-screens 01–07, 09 (underlay) | One screen; Attack / Defense / Utility tab + scroll variants |
| `hud_gem_claim` | hud_run overlay | gem-screen 01 | Timed CLAIM tile, bottom-left — **high priority** |
| `modal_wave_info` | modal | tower-screens 08 | WAVE INFO tab only; STATS tab not photographed |
| `overlay_hamburger` | menu | tower-screens 09 | Right-side icon grid over `hud_run` |
| `menu_cards` | menu | tower-screens 10, cont 01 | Same screen; inventory scroll |
| `menu_lab` | menu | cont 02 | Lab slots hub (beaker icon) |
| `modal_select_research` | modal | cont-2 01–05 | Research picker; scroll + search |
| `menu_challenges` | menu | cont-2 06 | Daily missions (checklist) + weekly challenge |
| `modal_exit_battle` | modal | — | **Not photographed** — Go Home vs Surrender |
| `modal_interrupt_research` | modal | — | **Not photographed** — confirm when interrupting a lab |

**Ignore for now (entry known, no deep map):** Shop (cart), Events (star), Modules (diamond), Guild (banner), Tournament (trophy), Ultimate Weapons (green tab).

**Follow-up shots (keep listed, do not chase yet):** Wave Info → STATS tab, Lab History, Speed Up sheet, Shop, UW panel, Modules, Events/Guild/Tournament, EXIT BATTLE confirm, interrupt-research confirm, non-empty daily mission rows, Settings (pause-on-menu toggle).

**Still thin:** gear/Settings contents; card equip interaction; exact Select Research open + start-tile behavior.

---

## Persistent chrome (almost every in-run shot)

Present on `hud_run` and visible behind many overlays:

| Element | Role | Example values seen |
|---|---|---|
| Cash `$` | In-run upgrade currency | 4.24K → 11.41K |
| Coins `C` | Meta / lab / workshop currency | 8.22K → 12.64K |
| Gems ◆ | Premium | 105 → 107 |
| Shop cart (gold) | Opens Shop (**ignore_for_now**; same as hamburger cart) | always top-right |
| Hamburger ≡ | Opens `overlay_hamburger` (**confirmed**) | always top-right |
| Speed `-` / value / `+` | Game speed | `x3.5` |
| Left mid panel | Tower: ATK, regen `/s`, coin mult, HP bar | ATK 318, regen 0.11/s, x1.75, 6.65K/6.65K |
| Right mid panel **Tier / Wave box** | Tier, Wave, enemy ATK/HP, wave progress · **tap opens `modal_wave_info`** (**confirmed**) | Tier 1, Wave 26→33 |
| **Gem CLAIM tile** (intermittent) | Timed free gems · **bottom-left** above left stats · see `hud_gem_claim` | e.g. gem `6` + CLAIM |
| Bottom tabs (4) | Upgrade category switch | Sword / Shield / Star / Ultimate Weapons (green △) |

**Off-menu currencies:** Cards / Lab / Challenges show Coins, Gems, green triangles; Lab also gold triangles; Challenges shows mission ribbon points.

**Mid-run overlays:** Combat **keeps going** while menus are open. Settings can change this to pause (**confirmed**; Settings UI not mapped). Gem CLAIM can appear while the hamburger is open (visible in gem-screen shot under expanded menu).

---

## 1. `hud_run` — Main combat + workshop upgrades

**Shots:**  
[`01_main-screen-utility.png`](../../screen-maps/tower-screens/01_main-screen-utility.png) · [`02`](../../screen-maps/tower-screens/02_main-defense.png)–[`03`](../../screen-maps/tower-screens/03_main-def-2.png) · [`04`](../../screen-maps/tower-screens/04_main-damage.png)–[`06`](../../screen-maps/tower-screens/06_main-damage-3.png) · [`07_main-utility-2.png`](../../screen-maps/tower-screens/07_main-utility-2.png)

**Classification:** `hud_run` (primary) + `upgrade` (bottom panel)

**Likely purpose:** Play the run; buy cash-priced workshop upgrades; change speed; open global menus.

**How opened:** Default battle screen.

**What leaves it:**
- Tap **Tier N / Wave #** box → `modal_wave_info` (**confirmed**)
- Hamburger ≡ → `overlay_hamburger` (**confirmed**)
- Top-right cart → Shop (**ignore_for_now**)
- Bottom tabs → Attack / Defense / Utility / Ultimate Weapons panels
- Death / EXIT BATTLE path → see hamburger
- Intermittent **gem CLAIM** (bottom-left) — claim in place; stays on `hud_run`

**Automation relevance:** `both` (OCR wave/cash/HP; click upgrades, tabs, speed, menus). **Always include opportunistic gem-claim tap** on HUD click passes.

### Bottom tabs → upgrade panels

| Tab | Header color / label | Automation note |
|---|---|---|
| Sword (blue) | ATTACK UPGRADES | Selected border glow |
| Shield (red/pink) | DEFENSE UPGRADES | |
| Star (yellow) | UTILITY UPGRADES | |
| Green △-in-circle | **Ultimate Weapons** | **ignore_for_now** — not photographed |

### Attack upgrades (scroll pages 04→05→06)

Each tile: **name · current value · `$` cost button**.

| Upgrade | Values seen | Costs seen |
|---|---|---|
| Damage | 318 | $10 |
| Attack Speed | 3.52 | $5 |
| Critical Chance | 56.00% | $231 |
| Critical Factor | x7.40 | $15 |
| Range | 36.50m | $14 |
| Damage / Meter | x1.0081 / m | $30 |
| Multishot Chance | 20.00% | $16 |
| Multishot Targets | 6 | $350 |
| Rapid Fire Chance | 12.80% | $20 |
| Rapid Fire Duration | 1.95 sec | $20 |
| Bounce Shot Chance | 18.40% | $20 |
| Bounce Shot Targets | 7 | $250 |
| Bounce Shot Range | 4.10m | $31 |

List completeness: **provisional OK** — Eric did not fully scroll-check; revisit later if buy bots miss a row.

### Defense upgrades (scroll 02→03)

| Upgrade | Values seen | Costs seen |
|---|---|---|
| Health | 6.65K | $15 |
| Health Regen | 0.11/sec | $7 |
| Defense % | 24.50% | $9 |
| Defense Absolute | 247 | $3 |
| Thorn Damage | 34% | $10 |
| Lifesteal | 2.15% | $10 |
| Knockback Chance | 19.00% | $10 |
| Knockback Force | 2.95 | $10 |
| Orb Speed | 2.95 | $15 |
| Orbs | 1 | $300 |

Same provisional completeness note as Attack.

### Utility upgrades (scroll 01→07)

| Upgrade | Values seen | Costs seen |
|---|---|---|
| Cash Bonus | x2.28 | $465 |
| Cash / Wave | 104 | $16 |
| Coins / Kill Bonus | x2.37 | $441 |
| Coins / Wave | 22 | $12 |
| Free Attack Upgrade | 14.50% | $8 |
| Free Defense Upgrade | 15.50% | $13 |
| Free Utility Upgrade | 1.00% | $16 |
| Interest / Wave | 0.00% | $15 |

Same provisional completeness note.

### Still open — `hud_run`

- Speed min/max and wrap vs clamp
- Floating `+1 Attack Range` (shot 01) — transient FX vs durable UI (likely ignore)

---

## 2. `modal_wave_info` — Tier/Wave battle report

**Shot:** [`08_stats-main.png`](../../screen-maps/tower-screens/08_stats-main.png)  
**Classification:** `modal`  
**How opened:** **Confirmed** — tap the **Tier N Wave #** box on `hud_run`.  
**Likely purpose:** Inspect run performance mid-run.  
**Automation relevance:** `read` (CSV-heavy); clicks mostly tab switch / close.

**Chrome:** Title `Tier 1 – Wave 32` · tabs **WAVE INFO** (active, badge `1`) · **STATS** (not photographed — follow-up) · close **X**.

### WAVE INFO fields (candidates for CSV)

**Battle Report**

| Field | Value seen |
|---|---|
| Game Time | 17m 52s |
| Real Time | 5m 48s |
| Coins Earned | 3.95K |
| Coins Per Hour | 40.92K |
| Cells Earned | 0 |
| Cells Per Hour | 0 |

**Records**

| Field | Value seen |
|---|---|
| Highest Coins / Minute | 727 |
| Largest Wave Skip | 1 |
| Most Coins From Wave Skip | 64 |
| Most Cells From Wave Skip | 0 |
| Largest Smart Missile Stack | 0 |
| Largest Golden Combo | 0 |
| Most Coins From Golden Combo | 0 |
| Largest Inner Landmine Charge | 0 |

**Damage** (list continues off-screen)

| Field | Value seen |
|---|---|
| Damage Dealt | 115.37K |
| Projectiles | 106.13K |
| Rend Armor | 0 |
| Death Ray | 0 |
| Thorns | 39 |
| Orbs | 9.19K |

### Still open

- What **STATS** tab shows (follow-up shot)
- Meaning of badge `1` on WAVE INFO
- Availability post-death / between runs vs mid-run only

---

## 3. `overlay_hamburger` — In-run side menu

**Shot:** [`09_hamburger-click.png`](../../screen-maps/tower-screens/09_hamburger-click.png)  
**Classification:** `menu` (overlay)  
**How opened:** **Confirmed** — tap hamburger ≡ on `hud_run`.  
**Automation relevance:** `click` (navigation hub). Combat continues underneath unless Settings → pause.

### Buttons (grid)

| # | Icon | Destination | Status |
|---|---|---|---|
| 1 | Shopping cart | Shop | **ignore_for_now** (same shop as top-right cart) |
| 2 | Green **X** | Close overlay → `hud_run` | **confirmed** |
| 3 | Checklist | Daily missions → `menu_challenges` | **confirmed** |
| 4 | Gear | Settings | Not mapped; contains pause-on-menu option |
| 5 | Cards / deck | `menu_cards` | **confirmed** |
| 6 | Beaker / flask | `menu_lab` | **confirmed** |
| 7 | Star | Events | **ignore_for_now** |
| 8 | Diamond / gem shape | Modules | **ignore_for_now** (follow-up) |
| 9 | Banner / flag | Guild | **ignore_for_now** |
| 10 | Trophy | Tournament | **ignore_for_now** |
| 11 | **EXIT BATTLE** | Opens confirm: **Go Home** (resume later) vs **Surrender** (end round) | Modal **not photographed** |

---

## 4. `menu_cards`

**Shots:** [`10_cards-1.png`](../../screen-maps/tower-screens/10_cards-1.png), [`cont/01_cards-2.png`](../../screen-maps/tower-screens-cont/01_cards-2.png)  
**Classification:** `menu`  
**How opened:** **Confirmed** — hamburger → Cards.  
**Exit:** Chevron `v` top-right · footer **Tap To Return To Game**.  
**Automation relevance:** `both` (buy packs; equip; later card-loadout events).

### Controls

| Control | Detail |
|---|---|
| Currencies | Coins, Gems, green triangles (15) |
| BUY NEW CARD info `i` | Help |
| Buy x1 | 20 gems (highlighted) |
| Buy x10 | 200 gems |
| ACTIVE | `5/5` slots |
| INVENTORY | Scrollable grid; stars + dupe progress `n/m`; green ✓ = equipped; padlock = locked/special |

### Active cards (5/5)

1. Enemy Balance  
2. Coins  
3. Cash  
4. Critical Coin  
5. **Wave Skip** (**confirmed**)

### Inventory cards spotted (merged both scrolls)

Damage, Attack Speed, Health, Health Regen, Range, Cash, Coins, Slow Aura, Critical Chance, Enemy Balance, Extra Defense, Fortress, Free Upgrades, Extra Orb, Plasma Cannon, Critical Coin, Wave Skip, Intro Sprint, + locked empty slots.

### Still open

- Tap inventory card → equip swap modal vs instant
- Padlock meaning on Enemy Balance / Plasma Cannon / Intro Sprint
- Whether card changes apply immediately mid-run

---

## 5. `menu_lab` — Lab slots hub

**Shot:** [`cont/02_lab-overall.png`](../../screen-maps/tower-screens-cont/02_lab-overall.png)  
**Classification:** `menu`  
**How opened:** **Confirmed** — hamburger → **beaker** icon.  
**Exit:** `v` · Tap To Return To Game.  
**Automation relevance:** `both` (queue research; rush; auto-queue toggle; interrupt).

### Currencies

Coins · Gems · green triangles (15) · gold triangles (20)

### Slots

| Slot | State | Detail |
|---|---|---|
| Lab 1 | Active | Game Speed Lv.5 · x3.5 » x4.0 · Rush 373 gems · ~2d 12h · Speed Up |
| Lab 2 | Active | Labs Speed Lv.12 · x1.22 » x1.24 · Rush 46 · ~6h 39m · Speed Up |
| Lab 3 | Active | Attack Speed Lv.7 · x1.12 » x1.14 · Rush 6 · ~46m · Speed Up |
| Lab 4 | Locked | Unlock for **1400** gems |

### Auto-queue control (**confirmed**)

- Clock icon with refresh ring: when **highlighted**, finishing research **auto-queues the same research** again.
- When **not** highlighted, research ends and the **slot opens**.
- You **can interrupt** an in-progress research to start another → confirm dialog (`modal_interrupt_research`, not photographed).

### Still open / more_info_needed

- Exact tap that opens `modal_select_research` (empty slot vs finished vs title) — needed before lab-queue events
- What **Speed Up** opens (follow-up)
- Max lab unlocks / account cap

---

## 6. `modal_select_research`

**Shots:** cont-2 [`01`](../../screen-maps/tower-screens-cont-2/01_lab-choice-1.png)–[`05_lab-search-example.png`](../../screen-maps/tower-screens-cont-2/05_lab-search-example.png)  
**Classification:** `modal`  
**How opened:** From Lab — **more_info_needed** before research-start events.  
**Exit:** **X** · Tap To Return To Game (may skip Lab?).  
**Automation relevance:** deferred until open + start-tile behavior known; treat pick UI as mapped for OCR only.

### Chrome

- Title **SELECT RESEARCH**
- Search… (demo query: `cash`)
- **History** (badge `1`) — not opened (follow-up)
- **Hide Completed** checkbox
- Collapsible category headers

### Categories seen

| Category | Examples |
|---|---|
| MAIN RESEARCH | Game Speed, Labs Speed (Researching…), Starting Cash, Workshop * Discount, Labs Coin Discount, Buy Multiplier, More Round Stats, Presets |
| ATTACK RESEARCH | Damage, Attack Speed (Researching…), Critical Factor, Range, Damage / Meter |
| DEFENSE RESEARCH | Health, Health Regen, Defense Absolute |
| UTILITY RESEARCH | Cash Bonus, Cash/Wave, Coins/Kill, Coins/Wave, Interest, Max Interest |
| PERKS RESEARCH | Unlock Perks Lv.1 (long: ~2d 20h, 1.49M coins) |

Tile pattern: **Name Lv.N** · effect `current » next` · duration · coin cost.  
**Researching…** overlays when that tech is already in a lab.  
**Pink/red border tiles** = **cannot afford** (coin cost too high) (**confirmed**).

### Blocked for events until known

- Tap tile → instant start vs confirm (**more_info_needed** — Eric: do not build research-start events yet)
- Whether interrupt path always required when all slots busy

---

## 7. `menu_challenges` — Weekly + Daily

**Shot:** [`06_challenges-no-challenges-right-now.png`](../../screen-maps/tower-screens-cont-2/06_challenges-no-challenges-right-now.png)  
**Classification:** `menu`  
**How opened:** **Confirmed** — hamburger → **checklist** (Daily missions).  
**Automation relevance:** `both` later (claim chests; mission progress); empty daily list in this shot → mission rows `ignore_for_now` until a filled capture.

### Visible state

| Element | Value |
|---|---|
| Currencies | Coins 12.64K · Gems 107 · triangles 15 · ribbon **125** |
| WEEKLY CHALLENGE | Reset in 4d 6h · completed **22/35** |
| Chests | 15 ✓ · 20 ✓ (badge 1) · 25 🔒 · 30 🔒 · 35 🔒 |
| Daily | **0/8 Missions** · “2 new missions in 6h 28m” · empty body |
| Exit | `v` · Tap To Return To Game |

### Still open

- Chest at 20 with badge — unclaimed reward?
- Daily mission row / claim layout when missions are present (follow-up)

---

## 8. `modal_exit_battle` (not photographed)

**How opened:** Hamburger → **EXIT BATTLE**.  
**Choices (**confirmed**):**
- **Go Home** — leave battle UI but **allows resume**
- **Surrender** — **ends the round**

Map this before any `exit_battle` automation. Follow-up shot recommended.

---

## Nav sketch

```
hud_run
  ├─ [bottom-left gem CLAIM] → claim gems (stay on hud_run)     [HIGH PRIORITY; ~10–15m]
  ├─ [Tier/Wave box] → modal_wave_info → [X] → hud_run          [confirmed]
  ├─ [≡ hamburger] → overlay_hamburger                          [confirmed]
  │     ├─ [X] → hud_run
  │     ├─ [checklist] → menu_challenges → [v/tap] → hud_run    [confirmed]
  │     ├─ [Cards] → menu_cards → [v/tap] → hud_run             [confirmed]
  │     ├─ [Beaker] → menu_lab → [v/tap] → hud_run              [confirmed]
  │     │     ├─ [clock+refresh highlight] ↔ auto-queue same    [confirmed]
  │     │     ├─ [interrupt busy lab] → confirm modal           [confirmed; no shot]
  │     │     └─ [?] → modal_select_research                    [more_info_needed]
  │     ├─ [cart] → Shop                                        [ignore_for_now]
  │     ├─ [star] → Events                                      [ignore_for_now]
  │     ├─ [banner] → Guild                                     [ignore_for_now]
  │     ├─ [trophy] → Tournament                                [ignore_for_now]
  │     ├─ [diamond] → Modules                                  [ignore_for_now]
  │     ├─ [gear] → Settings (pause-on-menu option)             [thin]
  │     └─ [EXIT BATTLE] → Go Home | Surrender                  [confirmed; no shot]
  ├─ [cart top-right] → Shop (same)                             [ignore_for_now]
  ├─ [bottom Sword|Shield|Star] → upgrade subpanel              [confirmed]
  ├─ [bottom green △] → Ultimate Weapons                        [ignore_for_now]
  └─ [upgrade tile $] → spend cash / bump stat                  [obvious]
```

---

## Candidate CSV / OCR fields (draft)

| Field | Screen(s) |
|---|---|
| cash, coins, gems | hud_run, overlays |
| tier, wave | hud_run, modal_wave_info title |
| tower_atk, regen_per_s, coin_mult, hp_cur, hp_max | hud_run mid-left |
| enemy_atk, enemy_hp | hud_run mid-right |
| game_speed | hud_run |
| game_time, real_time, coins_earned, coins_per_hour, cells_* | modal_wave_info |
| damage_dealt, projectiles, thorns, orbs, … | modal_wave_info Damage |
| active_cards[5] (incl. Wave Skip), card_levels | menu_cards |
| lab_slot_{n}_name, lab_slot_{n}_eta, lab_rush_gem_cost | menu_lab |
| lab_auto_queue_on | menu_lab (clock+refresh highlight) |
| research_name, research_eta, research_coin_cost, unaffordable | modal_select_research |
| weekly_completed, weekly_reset_eta, mission_points | menu_challenges |

---

## Candidate sequences (names only)

| Sequence | Ready? |
|---|---|
| `claim_gem_popup` | **Ready / high priority** — opportunistic bottom-left CLAIM; bake into other HUD click loops as just-in-case |
| `buy_cash_upgrade` | Ready enough (list provisional); still run gem-claim insurance on the same pass |
| `set_game_speed` | Thin (limits unknown) |
| `open_wave_info_snapshot` | Ready for OCR path |
| `hamburger_to_cards_equip` | Nav ready; equip interaction open |
| `hamburger_to_lab_*` | Nav + auto-queue known; **start/interrupt events blocked** until select-research + tile-tap known |
| `lab_rush_or_speed_up` | Follow-up (Speed Up sheet) |
| `claim_weekly_chest` | Thin |
| `exit_battle_go_home` / `exit_battle_surrender` | Choices known; need confirm UI shot |
| `buy_card_pack_x1/x10` | Nav + buttons known |

---

## Unknown / later

- Ultimate Weapons, Shop, Modules, Events, Guild, Tournament (ignore until needed)
- STATS tab of wave modal
- Lab History, Speed Up sheet
- EXIT BATTLE + interrupt-research confirm UIs
- Select Research: how opened; tile tap start vs confirm (**blocks research events**)
- Full upgrade list bottoms (provisional OK)
- Settings pause toggle location
- End-of-run / death / reward claim screens
- Workshop (permanent coin upgrades) if distinct from in-run cash panel

---

## Checklist

- [x] Per-screen classifications filled (draft)
- [x] Round-1 questions answered and folded back into this doc
- [x] Draft CSV/stat fields
- [x] Draft sequence names (+ readiness)
- [x] Missing / ignore / follow-up screens noted
