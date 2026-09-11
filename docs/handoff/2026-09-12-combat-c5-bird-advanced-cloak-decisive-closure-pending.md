# C5 Host combat — Bird Advanced Cloak decisive closure gate

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Why this gate exists

The raw-event runtime found the missing positive separator for the only factual Advanced-Cloak decisive row:

```text
680435/T31 ship68:
  explicit Host mine-hit report
  damage after hit = 55
  factual VCR starts objectid68 with damage=55
```

Official Host-order documentation states that a cloaked ship hitting a mine becomes uncloaked, including Advanced-Cloak ships.

Runtime checkpoint:

```text
docs/handoff/2026-09-12-combat-c5-bird-advanced-cloak-raw-event-runtime.md
```

## Active diagnostic

```text
tools/diagnostics/combat_host_bird_advanced_cloak_decisive_closure_audit.py
tests/test_combat_host_bird_advanced_cloak_decisive_closure_audit.py
```

The audit is deliberately narrow and uses only positive identity-safe evidence.

### Expected eligible row

For `680435/T31 ship68 vs26` it requires:

```text
exact target-specific "ID#68 has struck a mine" Host message
positive reported mine damage
factual VCR at the battle site containing objectid68
the VCR starting damage equals the reported mine-hit damage
```

Expected observed value:

```text
mine-hit damage=55
VCR damage=55
```

### Expected blocked rows

For `620694/T119 ship26/69 vs74` it requires only attribution controls:

```text
same owner at T
same hull at T
T damage=0
T iscloaked=true
```

T remains post-Host/postcombat and is not a production input. This closes historical attribution only.

## Strong acceptance

```text
factual_mine_decloak_closed=True
blocked_advanced_controls_closed=True
all_decisive_advanced_rows_explained=True
```

Expected counters:

```text
focus_rows=3
factual_rows=1
blocked_rows=2
explicit_target_mine_hit_rows=1
mine_hit_vcr_damage_match_rows=1
blocked_stable_t_cloak_true_rows=2
```

## Evidence boundary

If this passes, promote only the dynamic rule:

```text
Advanced Cloak + mine hit after cloak engagement -> uncloaked
```

as `DOCUMENTED + CORPUS_OBSERVED + TESTED`.

Do **not** make Host messages or T state canonical inputs. Do **not** claim population-wide Advanced-Cloak predictability until upstream mine/Glory/fuel state is reconstructed independently.

After this gate, resume the combined population-wide directional STANDARD targetability differential using supported ordinary-cloak Bird + DIFF_VERIFIED Privateer branches, while unresolved dynamic Advanced-Cloak states remain fail-closed.
