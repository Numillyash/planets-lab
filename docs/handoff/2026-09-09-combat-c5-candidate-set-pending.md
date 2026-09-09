# C5 Host combat — candidate-set differential — pending runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains open/draft. Game `591478` is excluded from ordinary promotion.

## Previous gate closed

The canonical ordinary STANDARD repeated-pair side helper is now runtime-tested.

User runtime source:

```text
de824ab4ecc0bc8cd32784ce4d3df9021eddd71b
```

Artifact:

```text
artifacts/combat-c5-queue-primitive-20260909-221345
```

Result:

```text
QUEUE PRIMITIVE TESTS
.................................................................... [100%]
tests rc=0
```

Therefore `src/planets_lab/rules/combat/queue.py` is `TESTED`. The underlying clean ordinary repeated-pair second-pass reversal remains `CORPUS_OBSERVED + DIFF_VERIFIED`; it is not promoted as primary `DOCUMENTED`.

## Why this gate exists

The factual-positive queue audit intentionally used an existing VCR as an oracle that a pair had reached combat. That was appropriate for validating pair phase/side composition, but it does not answer the next Host question:

```text
Given a combat site and reconstructed pre-combat state, which ship pairs are
eligible, blocked or unresolved before mutable target selection begins?
```

The new gate removes VCR presence as a positive pair-eligibility oracle.

## Committed diagnostic

```text
tools/diagnostics/combat_host_candidate_set_audit.py
tests/test_combat_host_candidate_set_audit.py
```

Schema:

```text
planets-lab.combat-host-candidate-set-audit.v1
```

## v1 evidence boundary

This is deliberately **site-conditioned and movement-conservative**. It is not yet a full post-movement stack predictor.

Factual VCR data supplies only:

- ordinary battle-site coordinate `(game, battle_turn, x, y)`;
- the held-out factual ship-pair set used for comparison after prediction.

It does **not** supply:

- positive pair eligibility;
- candidate ship membership at a site;
- fuel permission;
- diplomacy permission for the same pair.

Candidate ship membership is reconstructed from owner-current `T-1` only.

## Conservative stationary-position subset

A `T-1` ship is admitted to the v1 candidate stack only when its position can be treated as intrinsically stationary without solving the full movement phase:

- owner-current `T-1` record exists at the factual site coordinate;
- `warp == 0`;
- mission is not Tow (`6`), Intercept (`7`) or Cloak & Intercept (`20`);
- FC is not `HYP` case-insensitively;
- ship is not named as a target by any visible `T-1` Tow attempt;
- start coordinate is not an obvious Firecloud Chunnel source stack under the conservative source detector.

Excluded ships are a **movement coverage gap**, not a combat negative.

The diagnostic reports `movement_uncovered_ship_reasons` and keeps factual pairs whose member(s) fail this position gate out of candidate-set eligibility scoring.

## Fuel boundary

`T-1 neutronium > 0` is accepted as a positive fuel fact for the stationary v1 subset.

`T-1 neutronium <= 0` or missing is **not** treated as `False`: transfers and other pre-combat phases are not fully reconstructed here, so the canonical input remains `None` and the pair may stay unresolved.

Do not promote a zero-fuel blocker from this v1 audit.

## Diplomacy profiles

### strict

A requested Kill!/PE direction is accepted only when another factual ship combat in the same game independently proves that exact direction under the same raw T-1 relation signature.

Controls are:

- owner-current `T-1` aligned to factual VCR owners;
- one-sided Kill!/PE only;
- directional (`low_to_high` / `high_to_low`);
- raw relation signature only, with no semantic labels assigned to numeric relation values;
- leave-pair-out: all factual VCR rows for the exact candidate pair at the current site are removed from its control set.

If no independent control remains, requested diplomacy is `None`, not guessed `True`.

### conditional

Kill!/PE request is supplied as allowed aggression. This is an upper-bound composition profile used to separate pair-selection mechanics from diplomacy coverage. It is **not** an independent Host predictor.

## Interpretation hierarchy

After `tests rc=0` and `audit rc=0`, first require:

```text
payload_conflicts = 0
```

Then interpret candidate-covered factual pairs:

1. `conditional.factual_pair_status.blocked > 0`
   - strongest contradiction;
   - the canonical pair layer says an actually observed pair is impossible even after granting requested diplomacy;
   - inspect every row before changing mechanics.

2. `strict.factual_pair_status.blocked > 0`
   - also serious;
   - inspect calibration, FC, fuel, race/advantage and relation context before changing canonical rules.

3. factual `unresolved`
   - expected coverage gap from fuel, diplomacy, HWM/C&I or other tri-state inputs;
   - not a contradiction.

4. `eligible_nonfactual`
   - **not** a false-positive Host queue claim;
   - pair eligibility is broader than actual target selection, and a ship may be destroyed/captured or choose another target before that pair is reached.

## Site-level metrics

The strongest site subset has:

```text
all_factual_position_covered = true
all_candidate_resolved = true
```

For such sites, factual pairs should be a subset of the eligible pair set. A failure of:

```text
strict_factual_subset_of_eligible
conditional_factual_subset_of_eligible
```

is a concrete candidate-set contradiction in that profile.

Exact equality:

```text
eligible_set == factual_pair_set
```

is informative only for simple sites. It is **not** required generally because this gate does not yet implement the mutable target queue.

## What this gate does not prove

Do not describe v1 as full post-movement stack reconstruction. It does not yet solve:

- ordinary moving-ship endpoints;
- Tow outcome/release;
- Intercept/C&I movement;
- HYP arrival;
- full Chunnel membership;
- all pre-combat fuel transfers/drains;
- mutable target-list selection;
- capture/reinsertion;
- second-pass creation;
- ship-to-planet transition.

## Next decision

If the candidate-covered population has no hard factual blockers, keep pair eligibility unchanged and use the output to choose the next expansion:

- expand position reconstruction using already verified movement subsystems until factual-pair coverage is useful; and/or
- begin the mutable target-selection layer on clean fully reconstructed sites.

If hard factual blockers exist, audit them individually before implementing the queue. Do not weaken matching-FC, diplomacy, PIA/C&I or standard priority merely to reduce counters.
