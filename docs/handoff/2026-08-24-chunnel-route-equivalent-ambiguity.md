# Chunnel route-equivalent ambiguity follow-up

Date: 2026-08-24

Repository: `Numillyash/planets-lab`

Status: **Warp-0 Chunnel event-discovery gap rejected; route-equivalent multi-event ambiguity is the active production bug candidate.**

This handoff supersedes `2026-08-24-warp0-chunnel-gap-followup.md` for current priorities.

## Runtime baseline

The compiled movement accounting is still unchanged:

```text
post_external_residual              3938
chunnel_explained                   1387
post_chunnel_residual               2551
horwasp_strong_explained             240
post_horwasp_strong_residual        2311
```

No production accounting change has been made yet.

## Warp-0 structural Chunnel audit result

Focused diagnostic:

```text
tools/diagnostics/warp0_chunnel_gap_audit.py
```

Runtime result over the 119 Warp-0 self-waypoint external-move rows:

```text
structural_chunnel_match                22
numeric_fc_structural_match             22
structural_without_numeric_fc_match      0
existing_classifier_event_match         22
missed_by_existing_event_discovery       0
multi_candidate_same_route_groups        6
structural_chunnel_route_groups          9
```

Therefore the proposed **private/hidden friendly-code event-discovery gap is rejected** in this population. Every structural Chunnel match already has visible numeric-FC support and is already represented by the existing event discovery.

The multi-ship route evidence remains important. Examples include game `360690` turn `67`, where eight candidate rows share one Chunnel route and several Firecloud initiators are simultaneously valid for the same origin/destination pair.

## Production bug candidate

Both the standalone Chunnel evaluator and the compiled L2 label compiler currently build `matches` with this predicate:

```text
event.destination == observed_destination
AND event.pre_chunnel_position IS NOT NULL
AND candidate_pre_chunnel_position == event.pre_chunnel_position
```

Thus all events inside one `matches` list are already equivalent for the movement question: they describe the same candidate pre-Chunnel position and the same observed destination.

Current behavior is nevertheless:

```text
len(matches) == 1  -> Chunnel explained
len(matches) > 1   -> ambiguous_matching_events -> residual
```

This conflates **event identity ambiguity** with **movement-mechanic ambiguity**. If multiple independently observed Chunnel initiators explain exactly the same route, identifying which initiator carried a passenger is unnecessary to explain why the passenger moved.

A pure helper now defines the intended semantics:

```text
src/planets_lab/corpus/movement_chunnel_match.py
```

For a non-empty route-equivalent match set, movement is explained. If different matches imply different descriptive roles for the same ship, only the role category becomes `route_equivalent_multiple_roles`; Chunnel closure itself remains valid.

## Pre-fix all-corpus differential audit

New DB-only diagnostic:

```text
tools/diagnostics/chunnel_route_equivalent_ambiguity_audit.py
```

It reads the existing compiled DuckDB and reports every row with:

```text
chunnel_match_count > 1
```

including:

- total multiple-match rows;
- how many remain `post_chunnel_residual` and final residual;
- Warp-0 self-waypoint overlap;
- distribution by match count, game, hull and baseline category;
- final-residual examples.

Because the current production matcher itself already enforces identical pre-position and destination within each match set, this audit measures the exact population affected by route-equivalent event multiplicity.

Implementation commits:

```text
0e3c27b  Define route-equivalent Chunnel match semantics
3e0c800  Audit route-equivalent Chunnel ambiguity
```

## Immediate next step

Run the DB-only audit before changing L2 semantics:

```bash
docker compose run --rm -T lab \
  python -m py_compile tools/diagnostics/chunnel_route_equivalent_ambiguity_audit.py

docker compose run --rm -T lab \
  python -u tools/diagnostics/chunnel_route_equivalent_ambiguity_audit.py \
  | tee /tmp/chunnel_route_equivalent_ambiguity_audit.log
```

If the multiple-match residual population is material and matches the expected Warp-0 groups, the production follow-up is:

1. use the shared route-equivalent match helper in compiled L2 labels and standalone Chunnel evaluation;
2. treat every non-empty route-equivalent match set as Chunnel-explained;
3. preserve `chunnel_match_count` as provenance;
4. keep role ambiguity descriptive rather than movement-residual-producing;
5. bump compiled movement context-label schema so old label caches invalidate automatically;
6. add deterministic duplicate-initiator/same-route regressions;
7. rebuild L2 normally without `--rebuild` and compare exact residual deltas against this pre-fix audit.

## Guardrails

- Do not deduplicate events with different pre-Chunnel positions or different destinations; those never enter the same production `matches` set today.
- Do not infer private friendly codes. The 22 focused structural rows already have visible numeric-FC support.
- Multiple route-equivalent observed events prove a Chunnel route even when initiator identity is not unique; they do not prove which initiator carried a passenger.
- Do not alter L1 movement accounting for this fix; this is an L2 Chunnel classification correction.
- Keep the existing mode-aware/effective-topology Chunnel pre-position caveat separate unless runtime evidence intersects it.
