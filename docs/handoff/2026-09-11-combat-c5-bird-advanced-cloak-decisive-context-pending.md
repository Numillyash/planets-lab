# C5 Host combat — Bird Advanced Cloak decisive-context gate

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Why this gate exists

The Bird Super Spy population runtime passed every hard contradiction check:

```text
decisive_rows=4
decisive_match=1
decisive_mismatch=0
decisive_unresolved=3
blocked factual-pair regressions=0
```

All three decisive unresolved rows are Advanced Cloak. The ordinary-cloak ship202 residual remains a clean positive.

Runtime checkpoint:

```text
docs/handoff/2026-09-11-combat-c5-bird-super-spy-population-runtime.md
```

## Decisive contrast

Expected blocked:

```text
620694/T119 ship26  vs attacker74 — Resolute hull31, mission9, prior cloak=true
620694/T119 ship69  vs attacker74 — Resolute hull31, mission9, prior cloak=true
```

Expected eligible / factual pair:

```text
680435/T31 ship68 vs attacker26 — Resolute hull31, mission9, prior cloak=true
```

A blanket Advanced-Cloak blocker would therefore regress the factual ship68 pair.

## Documentation hypothesis

Official Planets.nu documentation gives a narrower Advanced Cloak model:

- Super Spy attempts to cloak according to cloak type;
- Advanced Cloak consumes no cloak fuel but still needs at least 1 KT fuel;
- ion storms/nebulae do not by themselves decloak Advanced Cloak;
- mine hits can damage and decloak;
- POP/TRG Glory Devices detonate after movement and can damage/decloak;
- post-movement Loki passes can decloak unless race Loki Immunity applies.

Sources:

```text
https://help.planets.nu/mis-super-spy
https://help.planets.nu/abil-advanced-cloak
https://help.planets.nu/cloak-details
https://help.planets.nu/abil-glory-device
```

## Active diagnostic

```text
tools/diagnostics/combat_host_bird_advanced_cloak_decisive_context_audit.py
tests/test_combat_host_bird_advanced_cloak_decisive_context_audit.py
```

The diagnostic reuses the full position-v3/candidate-set-v2 predictor for the target and for possible post-movement Loki/Glory sources. It reports, for each of the three decisive rows:

```text
target start position
full predicted final position and source
visible mine-route risk
prior cloak / T-1 damage / fuel
predicted final positions of foreign Glory Device ships
POP/TRG code and site colocation
predicted final positions of foreign Loki ships
post-movement Loki distance to battle site
T owner/hull/damage/fuel/iscloaked as attribution-only controls
```

## Interpretation

A clean causal-looking separation would be a pre-combat decloak signal present for factual ship68 but absent for skipped ship26/69.

Examples:

```text
ship68: postmove active Glory at site; ship26/69: none
ship68: postmove Loki exposure in a game without applicable immunity; ship26/69: none
ship68: another independently supported damage/fuel-loss branch; ship26/69: none
```

Absence of such a separator means Advanced Cloak remains unresolved. Do not promote a blanket Advanced Cloak targetability rule merely because two skipped rows exist.

## Evidence boundary

This is attribution-only. Predicted Glory/Loki colocation is not automatically a promoted Host rule. T is post-Host/postcombat and cannot feed precombat state. Canonical `selection.py` and `queue.py` remain unchanged.
