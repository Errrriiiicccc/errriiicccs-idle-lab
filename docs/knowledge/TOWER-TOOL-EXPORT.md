# The Tower — `tool_export.json` catalogue

**Status:** living knowledge (2026-11-09)  
**Source observed:** Rend App emulator import via BlueStacks ADB  
**On-disk copy (this machine):** `%APPDATA%\rendapp\emulator-imports\toolExport_unknown.json`  
**Sample stamp:** `ExportVersion=1`, `ExportedAt=2026-11-09T20:19:31.155Z`, `VersionNumber=1262`, `DataVersion=32`, ~258 KB, **437 top-level keys**

This is the game’s own structured save export — not OCR, not memory dumps. Rend already pulls it; Idle Lab can read the same file (or pull the same way).

---

## 1. Pipeline (how it lands on disk)

```
The Tower (Settings → tap Player ID text ×5)
        → writes tool_export.json inside the Android app sandbox
BlueStacks ADB (Rend bundles adb.exe; BlueStacks also has HD-Adb.exe)
        → Rend channel: adb-check-ready → adb-extract-save
        → %APPDATA%\rendapp\emulator-imports\toolExport_unknown.json
        → apply-emulator-import → userData.json (+ run history, labs, modules, …)
```

**Enable export (from Rend’s own error text):** In The Tower, open Settings and tap the text of your Player ID five times quickly.

**ADB actors on this machine:**

| Piece | Path |
| --- | --- |
| Rend App | `C:\Program Files\RendApp\RendApp.exe` |
| Rend ADB | `C:\Program Files\RendApp\resources\adb\adb.exe` (+ runtime copy under `%APPDATA%\rendapp\adb-runtime\`) |
| BlueStacks ADB | `C:\Program Files\BlueStacks_nxt\HD-Adb.exe` |
| Import cache | `%APPDATA%\rendapp\emulator-imports\toolExport_unknown.json` |
| Diagnostics | `%APPDATA%\rendapp\diagnostics\diagnostics.jsonl` |

Rend diagnostics name the device family `BlueStacks / LDPlayer / MSI App Player / MuMu Player`, transport `adb-emulator`. Successful loops are ~70–600 ms for `adb-extract-save`, then `read-latest-emulator-save` / `apply-emulator-import`.

**Related Rend artifacts (derived, not the raw export):**

| File | Role |
| --- | --- |
| `userData.json` | Rend’s normalized store (labs planner, modules, snapshots, `importLog`, …) |
| `run-monitor-samples.json` | Live run sampling / loadout context |
| `gamedata/catalog.json` | Relics/cosmetics index map (CDN catalog; **not** full card/lab name tables in this snapshot) |
| `profiles.json` | Local profile (`Errriiiccc`, game start date) |

---

## 2. Shape of the export

Flat JSON object. Types are mostly:

- **scalars** — currencies, toggles, wave/tier, identity
- **parallel arrays** — workshop/card/lab/UW indexed by game-internal enum order (names live in the client / catalog, not in the export)
- **small object lists** — modules, battle history, lab completions, bot/guardian presets
- **nested maps** — `Vault`, `CurrencyEarnedThisCycle` / `CurrencySpentThisCycle`

Header / identity:

| Key | Sample / notes |
| --- | --- |
| `ExportVersion` | `1` |
| `ExportedAt` | ISO UTC |
| `VersionNumber` | client build (`1262`) |
| `DataVersion` | save schema (`32`) |
| `InGuild` | bool |
| `UserName` | string |
| `AvatarId` | int |
| `GameStartedDate` | ISO UTC |
| `PlayTime` | float seconds (~300k ≈ 83 h in sample) |

---

## 3. Catalogue by domain

Counts are approximate groupings over the 437 keys in the observed file.

### 3.1 Currencies & wallets (~32)

**Balances:** `Coins`, `Gems`, `Stones`, `Medals`, `Cells`, `Keys`, `Tokens`, `Bits`  
**Module wallet:** `ModuleCannonShards`, `ModuleArmorShards`, `ModuleGeneratorShards`, `ModuleCoreShards`, `ModuleRerollCurrency`, `ModuleTickets` (+ `*Lifetime` variants)  
**Cycle maps:**

```json
CurrencyEarnedThisCycle.Currencies / CurrencySpentThisCycle.Currencies
→ gem, coin, ticket, medal, stone, cells, module_ticket,
  cannon_shard, armor_shard, generator_shard, core_shard,
  module_reroll, tokens, bits
```

### 3.2 Progress / tiers / waves (~35)

| Key | Shape |
| --- | --- |
| `CurrentTier` | int |
| `HighestWaveThisTier` | list[40] int |
| `RoundsStartedThisTier` | list[40] int |
| `HighestCoinsEarnedThisTier` / `HighestCellsEarnedThisTier` | list[40] |
| `HighestWavePerTierThisCycle` | list[40] int |
| `CurrentWave`, `HighestWaveReachedThisRound`, `RoundTime`, `RoundActiveBool` | live run |
| `Upgrade*TierUnlocked` / `*EverUnlocked` | list[20] bool × attack/defense/utility |
| pack unlocks | `StarterPackUnlockedBool`, `EpicPackUnlockedBool`, `DisableAdsUnlockedBool` |

### 3.3 Workshop & in-run upgrades

**Persisted workshop levels:** `UpgradeWorkshopLevel` / `Defense` / `Utility` — list[20] each  
**In-run levels:** `UpgradeLevel` / `UpgradeDefenseLevel` / `UpgradeUtilityLevel` — list[20]  
**Enhancements:** `EnhancementLevel` (+ defense/utility), tier unlocks, buy multipliers  
**Presets:** `PresetUpgradeWorkshop*` list[100], `WorkshopPresetName` list[5], `CurrentWorkshopPreset`  
**Buy multipliers / toggles:** `AttackBuyMultiplier`, `NukeAutomateToggle`, `DeathRayInstantKillToggle`, `SpawnAcceleratorToggle`, perk auto-pick, target priority, orb distances, free-upgrade locks

### 3.4 Cards (~15)

| Key | Shape |
| --- | --- |
| `CardLevel`, `CardCount`, `CardUnlocked`, `CardMasteryUnlocked`, `CardActive` | list[40] |
| `SlotsUnlocked` | int |
| `SlotPresetCardAssignedBool`, `SlotPresetCardInt` | list[140] (presets × slots) |
| `BattleStartSlotCard*` | list[140] |
| `CurrentPreset`, `PresetName` | 5 named card presets |
| `CardsBoughtTotal` | int |

### 3.5 Labs & research (~12)

| Key | Shape |
| --- | --- |
| `LabsUnlocked` | int |
| `LabLevel`, `LabResearchInt`, `LabActiveBool`, `LabSpeedUpSpeed`, `LabSpeedUpRemainingSeconds` | list[5] |
| `ResearchLevel`, `ResearchPercentComplete`, `ResearchCompleteDate` | list[260] |
| `ResearchesComplete` | int |
| `CompletedLabs` | list of `{dateCompleted, labNumber, level}` |
| `TotalCoinsSpentOnResearch` | float |

### 3.6 Ultimate weapons (~13)

`UltimateWeaponsSystemUnlocked`, `UltimateWeaponUnlocked` list[9], `UltimateWeaponLevel` / `SelectedLevel` list[27], on/plus toggles + plus levels, `SpotlightSmartMissilesOff`, `PoisonSwampStunOff`, first/banned perk indices.

### 3.7 Guardians & vault (~30)

`GuardianUnlocked`, chip slots/levels/skins, `GuardianPresets` (5), power/harmony node arrays, `Vault` (`UnlockedGroups`, `UpgradesLevel`, `HasViewedVault`, `FreeRespecsAvailable`, `LastRespecDate`).

### 3.8 Bots (~27)

Per-family presets (`FlameBotPresets`, `ThunderBotPresets`, `GoldenBotPresets`, `AmplifyBotPresets`, `BotBotPresets`) — each `{Unlocked, Active, Levels[4], SelectedLevels[4], PlusUnlocked, PlusLevel}`.  
Plus cooldown selected levels, `Synchronicity*`, `CurrentBotPreset`, `BotPresetName`.

### 3.9 Modules (~25)

| Key | Shape |
| --- | --- |
| `ModuleEquipped` | list[4] of module objects |
| `ModuleInventory` | list of module objects |
| `AssistModuleSlots` | list[4] |
| `ModulePresets` | list[5] `{PresetName, PrimaryModuleGuids, AssistModuleGuids}` |
| pity / obtain / shatter / merge counters | scalars |
| substat ban + auto-reroll lists | currently empty in sample |

**Module object fields:** `Guid`, `InfoIndex`, `CurrentRarity`, `Level`, `MaxLevelReached`, `Effects[8]`, `EffectLocked[8]`, `IsNew`, `CoinsSpent`, `ShardsSpent`, `Favorite`, `RerollCounter`.

### 3.10 Relics & cosmetics (~10)

`RelicsUnlocked` list[350], `ProfileRelics`, tower/background/menu/banner unlock arrays list[100], selected indices, `TotalSkinsBought`.

### 3.11 Guild / tournament (~5)

`LeagueID`, `HighestLeague`, `LastGuildSeason`, `TournamentRecords` list of `{TournamentNumber, Date, LeagueID, Wave, Rank}`, preset indices for tournament/tier/dissonance.

### 3.12 Events / dissonance / milestones (~10)

`MilestonesPremiumUnlocked`, `MilestonesRewardClaimed` list[575], dissonance active/selected + boost arrays, `TrackAvailable` list[12].

### 3.13 Global presets (~3–6)

`GlobalPresets` list[6]: `{PresetName, WorkshopIndex, CardsIndex, BotsIndex, ModulesIndex, GuardiansIndex}` plus `CurrentGlobalPreset`, `TierPreset`, `TournamentPreset`, `DissonantPreset`.

### 3.14 Lifetime stats (`Total*` — ~81)

Career counters: damage, kills by enemy type and by source (orbs, thorns, UWs, bots, guardian), coins/gems/stones/medals/cells/keys/tokens/bits earned & spent, free upgrades, waves completed/skipped, workshop spend, enhancement spend, etc.

### 3.15 This-round stats (`*ThisRound` — ~73)

Live (or last) run telemetry: wave, enemies by type, damage by source, coins/cash/cells/gems, free upgrades, blocks/regen, guardian/bot yields, skip stats, CPM peaks, real vs gameplay time. Sample had `RoundActiveBool=true`, wave **582**, ~5.5k real-time seconds.

### 3.16 History objects

**`BattleHistory`** — list[30], **148 fields each**. Per-run archive: tier/wave/times, earnings, damage taken/dealt by source, kills by type/source, guardian/bot yields, dissonance type, kill cause (`KilledBy`).

**`WrappedStats`** — list[1] year wrap: tournament promo/demo, UW usage, deaths/kills by enemy type, battles started/surrendered, daily/event missions, cards pulled, etc. Several damage fields are `{…}` dicts (amount + companion metric).

---

## 4. What Rend applies from it

From `userData.json` → `importLog`, successful emulator imports apply subsets such as:

`labs`, `workshop`, `workshopPlus`, `ultimateWeapons`, `guardians`, `workshopPresets`, `dissonance`, `vault`, `cards`, `cardPreset`, `relicsThemes`, `modules`, `modulePreset`, `snapshot`, `runs`, `tournaments`, `saveDerivedState`

So the raw export is richer than what Rend’s UI necessarily surfaces — Idle Lab can use fields Rend ignores (especially live `*ThisRound` and dense `BattleHistory`).

---

## 5. Idle Lab implications

| Need | OCR | Export |
| --- | --- | --- |
| Wave / coins / gems / cells / tier | fragile HUD OCR | **shipped** — `tool_export` action → `stat_collect` atom (Persistent state) |
| Workshop / card / lab levels | mostly invisible | available in file; map more fields as needed |
| Run CPM / kill breakdown | partial / none | `*ThisRound` + `BattleHistory` (not all mapped yet) |
| Button affordances / panel open | visual | **no** — export has no UI geometry |

**Shipped hook:** action type `tool_export` reads `%APPDATA%\rendapp\emulator-imports\toolExport_unknown.json` (optional `path`, `map`, `max_age_s`). Atom id stays `stat_collect` (LCO **V** / molecules); title is **Persistent state**, interval 30s when pooled.

**Vision:** [VISION.md](../VISION.md) treats first-party exports as a legitimate sense channel; actuation stays ordinary input.

---

## 6. Gaps / follow-ups

1. Confirm on-device Android path of `tool_export.json` (Rend finds it; we haven’t logged the path string yet).
2. Map array indices → human names (cards, labs, UW, workshop rows) — catalog on disk only covers relics/cosmetics in this snapshot; may need Rend’s in-app tables or a scraped enum sheet.
3. Measure how often The Tower rewrites the export mid-run vs only on settings/export trigger.
4. Decide Idle Lab ownership: read Rend’s cache vs own ADB pull (avoid fighting Rend’s adb server).
5. Schema-diff when `DataVersion` / `ExportVersion` bumps.
)
