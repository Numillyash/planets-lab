# C5 Host combat — Bird Advanced Cloak raw-event / hidden-context gate

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains excluded.

## Previous gate

Runtime:

```text
docs/handoff/2026-09-11-combat-c5-bird-advanced-cloak-decisive-context-runtime.md
```

The focused post-movement context audit over the three decisive Advanced Cloak rows found no visible separator:

```text
focus_rows=3
expected_blocked_rows=2
expected_eligible_rows=1
postmove_active_glory_possible_rows=0
postmove_loki_possible_rows=0
```

The candidate-set-v2 visible mine-route signal is also clear for all three rows.

Factual control:

```text
680435/T31 ship68 vs attacker26
expected eligible / factual pair
Resolute Advanced Cloak / Bird Super Spy
full position source=normal_move_warp_well
visible mine risk=None
no postmove Glory
no postmove Loki
```

Skipped controls:

```text
620694/T119 ship26 vs74
620694/T119 ship69 vs74
expected blocked
same Advanced Cloak / Super Spy shape
visible mine risk=None
no postmove Glory/Loki within range
both stable at T with iscloaked=true
```

Attacker ship26 in the factual `680435/T31` pair has mission3=`Kill!`; the pair is therefore a valid ordinary-STANDARD negative control rather than a pre-standard mission artifact.

## Why raw events are next

A visible-state explanation has been exhausted without finding a separator. Remaining high-value possibilities include:

- a mine/web hit reported by Host but absent from owner-visible T-1 minefield geometry;
- Hidden Minefields or another campaign/race advantage;
- a mechanical cloak/damage/fuel report not represented in the normalized candidate state;
- another raw Host event/report field around the target ship or battle site.

Message absence is **not** proof that no event occurred. Only positive reports or explicit game configuration should be promoted as evidence.

## Active diagnostic

```text
tools/diagnostics/combat_host_bird_advanced_cloak_event_audit.py
tests/test_combat_host_bird_advanced_cloak_event_audit.py
```

The audit reads raw `.trn` members directly for narrow windows around the two cases:

```text
680435: turns 30,31,32; focus ships 68 and26; site (1984,2266)
620694: turns 118,119,120; focus ships 26,69,74; site (1590,1837)
```

It reports:

1. owner3 active advantages and relevant names (`mine`, `cloak`, `Loki`, `hidden`, etc.);
2. owner3 settings and visible minefield inventory;
3. focus-ship raw timeline from all available perspectives;
4. messages that either directly reference a focus object, occur at the exact battle site with mechanical wording, or mention a focus ship/name with mechanical wording;
5. sanitized event/report records that directly reference focus IDs or site coordinates;
6. matching VCR records.

Free-form text is exposed only for tightly matched focus messages. Other event records suppress text fields and preserve mechanical scalar/type metadata.

## Interpretation order

For `680435/T31 ship68`, prefer positive evidence in this order:

```text
explicit mine/web hit or cloak-failure message
explicit hidden-mine/campaign advantage + compatible mechanical report
explicit damage/decloak/Loki/Glory report
other typed mechanical event referencing ship68
```

Then compare the same categories against the skipped `620694/T119 ship26/69` controls.

If no positive separator exists, Advanced Cloak stays `UNRESOLVED`; do not infer targetability from missing messages.

## Evidence boundary

Canonical `selection.py` and `queue.py` remain unchanged. The ordinary Bird ship202 closure and Privateer Rob closure remain valid and should not be reopened merely because Advanced Cloak is unresolved.
