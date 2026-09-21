# Combat diagnostics feature-scope migration — pending runtime

Date: 2026-09-21

Repository: `Numillyash/planets-lab`
Branch: `main`

## Purpose

Feature Index v1 is now being used to replace ad-hoc historical game-id exclusions
inside combat diagnostics.

This changes **population selection plumbing only**. It does not change combat
mechanics, replay, transition formulas, or evidence labels.

## Why a second combat profile is required

The existing historical C3/C4 "ordinary" scope was defined as the current
12-game corpus excluding special/campaign/Horwasp-heavy game `591478`.

That old 11-game scope is **not** the same population as the strict
`ordinary-classic` profile, which selects only:

```text
360690
511506
620694
```

Replacing the legacy scope directly with `ordinary-classic` would silently
change the historical population and invalidate continuity with the existing
C3/C4 checkpoints.

Therefore Feature Index v1 now also defines:

```text
combat-planar-no-horwasp
```

with factual predicates:

```text
game.status == 3
settings.sphere == false
population.horwasp_present == false
```

On the current 12-game index this selects 11 games and excludes one:

```text
selected:
  360690
  511506
  620636
  620694
  620917
  621103
  621253
  621896
  622476
  680435
  680910

excluded:
  591478

UNKNOWN:
  none
```

The profile name intentionally describes the factual predicates rather than
claiming that every selected game is strict Classic.

## Migrated diagnostics

The following diagnostics no longer special-case game id `591478` when
constructing their clean/report scopes:

```text
tools/diagnostics/combat_planet_chain_audit.py
  schema -> planets-lab.combat-planet-chain-audit.v2

tools/diagnostics/combat_ship_chain_phase_audit.py
  schema -> planets-lab.combat-ship-chain-phase-audit.v2

tools/diagnostics/combat_ship_chain_cluster_audit.py
  schema -> planets-lab.combat-ship-chain-cluster-audit.v2
```

Each accepts:

```text
--feature-index
--scope-profile
```

Default scope profile:

```text
combat-planar-no-horwasp
```

Each report now emits:

```text
scope_selection.profile
scope_selection.included_game_ids
scope_selection.excluded_game_ids
scope_selection.unknown_game_ids
```

Report partitions use:

```text
profile_selected
profile_excluded
profile_unknown
```

instead of a hardcoded `game_591478` branch.

UNKNOWN profile games fail closed into the UNKNOWN scope rather than being
silently treated as ordinary.

## Continuity acceptance target

The selector-backed scope must reproduce the established C3/C4 checkpoint
population exactly.

C4 repeated planet target:

```text
profile_selected_all:
  transitions=103
  match=102
  not_comparable=1
  starbase=92
  no_starbase=11
  shield carry=103/103
```

C3 ship sequence targets:

```text
profile_selected_all:
  transitions=1169
  match=1138
  reappearance_after_capture=23
  mismatch=8

profile_selected_ship_vs_ship_survivors:
  764/764 match

profile_selected_ship_vs_ship_survivors_gap1:
  751/751 match

profile_selected_ship_to_planet_boundary:
  transitions=397
  match=374
  reappearance_after_capture=15
  mismatch=8
```

The cluster partition must retain:

```text
selected same-location transitions=1169
excluded same-location transitions=316
```

These are continuity assertions only. Passing them does not create a new
mechanics evidence status.

## Reproducible gate

Tracked gate:

```bash
bash tools/run-combat-feature-scope-gate.sh
```

It:

1. checks clean current `main`;
2. rebuilds the project Docker image;
3. runs feature-index and migrated combat tests;
4. rebuilds the archive-enriched Feature Index;
5. prints the `combat-planar-no-horwasp` selector result;
6. runs C4 planet-chain diagnostic;
7. runs C3 phase diagnostic;
8. runs C3 mismatch-cluster diagnostic;
9. runs the continuity checker.

Checker:

```text
tools/diagnostics/combat_feature_scope_integration_check.py
schema: planets-lab.combat-feature-scope-integration-check.v1
```

Acceptance requires:

```text
exact=true
failures=[]
```

## Evidence boundary

The feature index still remains selection infrastructure only:

```text
selector match
!= mechanic observation
!= discriminator
!= DIFF_VERIFIED
```

Existing C3/C4 conclusions remain unchanged unless an archive runtime exposes a
population drift or contradiction.
