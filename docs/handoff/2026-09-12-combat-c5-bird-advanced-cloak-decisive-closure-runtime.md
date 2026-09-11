# C5 Host combat — Bird Advanced Cloak decisive closure runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded from ordinary promotion.

## Runtime

Source HEAD:

```text
a3412e419b156296d08fac946eb63ff1d09799e4
```

Targeted tests:

```text
14 passed
```

Diagnostic:

```text
tools/diagnostics/combat_host_bird_advanced_cloak_decisive_closure_audit.py
```

Runtime artifact:

```text
artifacts/combat-bird-advanced-cloak-decisive-closure.json
```

## Result

```text
focus_rows=3
factual_rows=1
blocked_rows=2
explicit_target_mine_hit_rows=1
mine_hit_vcr_damage_match_rows=1
blocked_stable_t_cloak_true_rows=2
```

Acceptance:

```text
factual_mine_decloak_closed=True
blocked_advanced_controls_closed=True
all_decisive_advanced_rows_explained=True
```

## Factual eligible control — 680435/T31 ship68

T-1 owner-current state:

```text
Bird owner3
Resolute hull31 / Advanced Cloak
mission9 Super Spy
damage=0
fuel=480
iscloaked=true
```

Host produced an identity-safe mine-hit report for the exact target ship:

```text
ship68 struck a mine
reported damage=55
hit position=(1989,2273)
```

The factual VCR at `(1984,2266)` contains the same `objectid=68`, hull31/race3, entering combat with `damage=55`.

Closure reason:

```text
explicit_mine_hit_matches_positive_vcr_damage
```

This is the missing dynamic separator. Official cloak mechanics document that a cloaked ship which hits a mine during movement is decloaked. Advanced Cloak does not exempt the ship from mine-hit decloaking. The corpus therefore does not show a healthy Advanced-Cloak Super Spy being targetable here; it shows a previously cloaked ship damaged/decloaked before combat.

## Blocked controls — 620694/T119 ship26 and ship69

Both targets are Bird owner3 Resolute hull31 / mission9 Super Spy with prior `iscloaked=true`, `damage=0`, and positive fuel.

At T both IDs are stable same-owner/same-hull identities and remain:

```text
damage=0
iscloaked=true
```

Neither target appears in a factual VCR against attacker74. Closure reason for each:

```text
stable_same_ship_t_cloak_true_damage0_attribution
```

T remains attribution-only and is not a valid production precombat input. Its role here is to close the historical control, not to reconstruct future state.

## Evidence boundary

The three previously decisive-unresolved Advanced Cloak population rows are now historically explained:

```text
680435/T31 ship68  -> mine-hit damage/decloak -> factual combat
620694/T119 ship26 -> retained cloak attribution -> skipped
620694/T119 ship69 -> retained cloak attribution -> skipped
```

Evidence status for the decisive contrast:

```text
Advanced Cloak + mine-hit decloak path:
  DOCUMENTED + CORPUS_OBSERVED + TESTED

three decisive Advanced Cloak population rows:
  CORPUS_OBSERVED + TESTED, all historically explained
```

This does **not** promote a universal predictive Advanced-Cloak state resolver. Production state must ultimately come from the reconstructed precombat movement/mine/Glory/Loki/fuel pipeline, never from Host messages or T state.

Canonical `selection.py` and `queue.py` remain unchanged at this checkpoint.

## Next gate

Compose all currently supported directional ordinary-STANDARD targetability evidence over the full initial-selector baseline:

- DIFF_VERIFIED Privateer Rob ordinary-cloak blocks;
- documented/corpus-tested Bird ordinary Super Spy blocks;
- the two historically closed Advanced-Cloak blocked controls;
- the mine-hit ship68 row as an explicit eligible control only.

Require:

```text
all upstream gates clean
zero supported blocked factual pairs
zero potential first-selector regressions
strict exact-set baseline remains exact
conditional exact-set baseline remains exact
all four original broad mismatch profiles repaired
advanced factual mine-hit control remains eligible
```

Only after that population composition gate should directional targetability be wired into the canonical first STANDARD selector.
