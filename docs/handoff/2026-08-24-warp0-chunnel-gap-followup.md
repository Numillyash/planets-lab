# Generic movement residual — warp-zero Chunnel-gap follow-up

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **warp-zero tow/storm audit complete; broad tow and storm explanations rejected; missed Chunnel/group-transport discovery is the active focused investigation.**

This handoff supersedes `2026-08-24-warp0-external-movement-followup.md` for current priorities.

## Runtime baseline

The compiled 12-game movement baseline is unchanged:

```text
move_most_candidates              227468
post_external_residual              3938
post_chunnel_residual               2551
post_horwasp_strong_residual        2311
```

No production classifier has changed during the generic residual diagnostics.

## Warp-zero external-movement audit result

Focused diagnostic:

```text
tools/diagnostics/warp0_external_move_context_audit.py
```

Population:

```text
candidate_rows                               119
has_colocated_same_destination_comover        31
single_colocated_same_destination_comover       7
visible_explicit_tow_target_match               4
has_hidden_or_unresolved_comover                0
has_visible_non_tow_comover                    31
effective_topology_storm_vector_match           0
```

The 119 rows span 35 hull IDs and 8 games.

Interpretation:

- visible explicit tow explains only `4 / 119`, so ordinary observed tow is not the broad missing context;
- no hidden/unresolved co-mover was found by the current owner-visibility test, so there is no evidence here for a large enemy/private-tow gap;
- effective-topology storm-vector matches are `0`, including game `591478`, so the active residual is not a remaining 2170 sphere/storm coordinate bug;
- 31 rows do participate in same-origin/same-destination group movement, all with visible non-tow co-movers;
- several group movements contain many ships moving together, which is transport-like rather than pairwise-tow-like.

## Strong Chunnel-like lead

A particularly strong example occurs in game `360690`, turn `67`:

```text
origin       (1792, 1235)
destination  (1684, 1085)
vector       (-108, -150)
distance     184.835 ly
```

Eight residual ships leave the same origin and arrive at the same destination in the same turn with Warp 0 / self-waypoint geometry. The group contains multiple hull-56 ships among the moving population.

Hull `56` is the Firecloud Class Cruiser in the standard ship list and carries both `Chunnel Initiator` and `Chunnel Target` abilities. Official Planets.nu Chunnel behavior explicitly allows the initiator and other co-located ships to be transported together through the Chunnel. This is a much better causal fit for a multi-ship group than ordinary towing.

The existing L2 Chunnel classifier does not classify these rows, therefore the next question is not "does Chunnel exist?" but **why did observed-event discovery fail to reconstruct this Chunnel-like group?**

Likely failure surfaces include:

- numeric friendly code is not owner-visible in the available perspective even though geometry/abilities identify the event;
- event discovery is too dependent on explicit initiator FC rather than structural origin/destination evidence;
- initiator/target visibility or owner resolution is incomplete;
- source-side pre-Chunnel geometry is reconstructed too narrowly;
- mode-aware storm/effective-topology pre-Chunnel position may eventually need to be centralized if the structural evidence is broad.

## New focused diagnostic

Implemented:

```text
tools/diagnostics/warp0_chunnel_gap_audit.py
```

Implementation commit:

```text
2846bed  Audit warp-zero residuals for missed chunnels
```

The first pass is deliberately conservative and tests same-origin initiators only. For each warp-zero external-move residual it searches for:

1. a ship with stable `Chunnel Initiator` ability at the candidate origin;
2. that initiator arriving at the candidate's observed destination;
3. a stable `Chunnel Target` ability ship already at that destination before the event and still there afterwards;
4. initiator and target having the same known owner;
5. target Warp 0;
6. target fuel >= 1 KT when visible;
7. initiator fuel >= 50 KT when visible;
8. effective-topology source/destination distance >= 100 ly;
9. numeric friendly-code match to target ID when the owner-visible FC is available.

It also compares structural matches to the existing `discover_observed_chunnel_events()` output. A structural match with no existing event is direct evidence of an event-discovery gap, while a numeric-FC structural match is stronger still.

The diagnostic never invents a hidden friendly code. `numeric_fc=None` remains unknown rather than inferred.

## Immediate next step

Run:

```bash
docker compose run --rm -T lab \
  python -m py_compile tools/diagnostics/warp0_chunnel_gap_audit.py

docker compose run --rm -T lab \
  python -u tools/diagnostics/warp0_chunnel_gap_audit.py \
  | tee /tmp/warp0_chunnel_gap_audit.log
```

Interpret these first:

```text
structural_chunnel_match
numeric_fc_structural_match
structural_without_numeric_fc_match
existing_classifier_event_match
missed_by_existing_event_discovery
multi_candidate_same_route_groups
structural_chunnel_route_groups
```

Decision rule:

- if structural Chunnel coverage is material and many matches are missed by current event discovery, fix/genericize Chunnel event reconstruction before touching any unrelated mechanic;
- if only a few rows match, keep them as a small race-specific contributor and return to the remaining non-group warp-zero residuals;
- do not classify group movement as Chunnel from vector coincidence alone.

## Other current conclusions

- scoped sphere topology for game `591478`: `CORPUS_OBSERVED + TESTED + DIFF_VERIFIED`, closed;
- classic/cloudy ion-storm handling: closed for current evidence;
- generic fuel-limited movement: real but minor (`7` strict signatures among `216` short-forward rows), no broad L1 promotion yet;
- Red Mite research remains closed;
- known Horwasp hull IDs `201-213` remain excluded from generic prioritization.
