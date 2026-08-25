# Web Drain raw metadata discovery

Date: 2026-08-25

Repository: `Numillyash/planets-lab`

Status: **fuel-proration v6 remains verified at post-fuel endpoint 2220. Crystal-owner Web Drain retains one exact causal-compatible case, but diplomacy/game-era verification is unresolved because the privacy-safe mechanics projection intentionally strips game metadata and diplomacy fields. The active task is direct raw `.trn` schema discovery.**

This handoff supersedes `2026-08-25-web-drain-diplomacy-followup.md` for active work.

## Verified production baseline

```text
post_mine_strong_residual           2226
fuel_proration_explained               6
post_fuel_proration_residual        2220
label_issues                           0

generic_rows                         763
generic_hulls                         76
dominant short-forward               116
```

No production schema/accounting change is part of this follow-up.

## Crystal-owner differential

The stricter owner-aware Web Drain audit found:

```text
all_enemy_web_at_origin                    79
crystal_owner_web_at_origin                79
non_crystal_owner_web_at_origin             0
crystal_web_raw_sufficient_to_insufficient  4
crystal_web_drain_causal_exact              1
```

Inside the dominant 116-row family:

```text
crystal_owner_web_at_origin                61
crystal_web_raw_sufficient_to_insufficient  3
crystal_web_drain_causal_exact              1
```

The exact case remains game `360690`, turn `44`, ship `489`, hull `53`; it matches only when 25 KT is removed from both fuel and movement mass.

## Diplomacy inspector result

The first diplomacy/game-era inspector found all four candidates but returned:

```text
teamid = None
same_nonzero_team = False
game_metadata = {}
relation_records = []
```

for the selected owner perspectives.

This is **not evidence of neutral diplomacy**. `src/planets_lab/corpus/normalizer.py::mechanics_projection()` intentionally reduces:

```text
game      -> {id, turn}
players   -> {id, raceid}
settings  -> privacy-safe mechanics subset
```

so creation dates, team/diplomacy metadata and relation records cannot survive into prepared snapshots unless explicitly projected.

Do not weaken that privacy boundary merely for this diagnostic.

## Current documented game-era concern

Current Planets.nu documentation describes time-varying Standard web diplomacy behavior, including changes around 2021-01-01 and 2023-12-09. Therefore the exact case cannot be assessed for Full-Alliance immunity until the actual game era and raw relation/team data are known.

## Active diagnostic

```text
tools/diagnostics/web_drain_raw_metadata_discovery.py
```

It reads the raw `validation/corpus/cache/loadall/game-<id>.zip` `.trn` members directly for the four candidates and reports only privacy-safe schema/provenance information:

```text
top-level keys and shapes
safe game metadata fields
settings keys related to dates/host/team/relation/alliance/diplomacy
player excerpts for target/web slots limited to race/team/relation-like fields
recursive paths whose key names match creation/start/date/year/host/team/relation/alliance/diplomacy/passage
```

It never prints values for names, email, username, savekey, password, API keys, secrets, messages or notes.

## Immediate next steps

1. pull current `main` and confirm clean tree;
2. syntax-check `tools/diagnostics/web_drain_raw_metadata_discovery.py`;
3. run it against the local raw archives;
4. inspect candidate `360690 / turn 44` first;
5. identify exact raw JSON paths for game creation/host era and diplomacy/team relations if present;
6. build a narrow deterministic extractor only after paths are observed;
7. if raw loadall lacks required metadata, use a separate public game-info source for game era and leave non-observable diplomacy unresolved rather than guessing;
8. keep Web Drain evidence-only until immunity compatibility is attributable.

Closed mechanics remain closed absent contradictory evidence. Fuel-proration v6 is **DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED**.