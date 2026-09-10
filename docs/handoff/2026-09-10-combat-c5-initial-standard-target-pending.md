# C5 Host combat — initial plain-STANDARD target selection pending runtime

GitHub is the source of truth. PR #28 remains draft/open and unmerged. Game `591478` remains isolated from ordinary promotion.

## Dependency closed: candidate-set v2

Read:

```text
docs/handoff/2026-09-10-combat-c5-candidate-set-v2-runtime.md
```

Runtime source:

```text
c804575f4275f4454dbb282d9fcfc99fad0700d6
```

Result:

```text
tests rc=0
audit rc=0
payload_conflicts=0
factual_unique_pairs=1986
candidate-covered factual pairs=428
conditional factual eligible=427
conditional factual unresolved=1
conditional factual blocked=0
conditional eligible nonfactual=331
all factual positions covered sites=242
conditional factual subset of eligible sites=236
conditional eligible exactly factual sites=171
```

Candidate-set v2 therefore provides a broad clean positive differential for pair eligibility but intentionally does not explain why 331 other eligible physical pairs never reach a VCR.

## Primary documented ordering boundary

Current Planets.nu Order Of Battle documentation states that:

- Priority Intercept occurs before standard ship-vs-ship combat;
- ships then fight according to Combat Priority;
- each starship can start combat with each other starship and proceeds through its target list while alive and uncaptured;
- when a selected opponent is blocked by matching Friendly Code, the ship proceeds to the next-highest-priority opponent;
- numeric FC / Kill! / Primary Enemy / Ship ID define the standard Combat Priority order.

This supports a narrow pre-mutation hypothesis for a plain STANDARD site:

```text
first active ship = highest-priority ship that has an eligible target
first target      = highest-priority eligible target for that active ship
```

Do not yet generalize this to post-fight survivor/capture continuation.

## New diagnostic

```text
tools/diagnostics/combat_host_initial_standard_target_audit.py
tests/test_combat_host_initial_standard_target_audit.py
```

Schema:

```text
planets-lab.combat-host-initial-standard-target-audit.v1
```

The audit reconstructs the same position-derived candidate context as candidate-set v2, including the visible T-1 foreign mine/web fail-closed gate. It then evaluates both strict leave-pair-out diplomacy and conditional aggression profiles.

Strong plain-STANDARD comparison requires:

1. every factual ship position at the site to be independently exact;
2. every physical candidate engagement decision in the profile to be resolved;
3. every eligible candidate to resolve to ordinary `standard` phase;
4. every eligible candidate to have a supported static battle-priority key;
5. predicted first-pass side orientation to equal the static higher-priority ship on RIGHT;
6. the factual pair set to be a subset of the eligible candidate set.

The exact-set control additionally requires:

```text
eligible candidate pairs == factual unordered pair set
```

Sites containing eligible PIA/C&I, unsupported FC priority, unresolved standard side, or a non-plain STANDARD side override such as Galactic Power are excluded from this narrow target-list population rather than retuned.

## What is tested

For each comparable site, the main selector orders eligible first-pass pairs by:

```text
(active standard_battle_priority_key, target standard_battle_priority_key)
```

and compares the minimum row to the **first factual ship VCR** at the site.

The audit reports:

```text
strict.broad
strict.exact_set
strict.ranks
conditional.broad
conditional.exact_set
conditional.ranks
exclusion_reasons
```

Important per-scope counters include:

```text
sites
multi_candidate_sites
first_pair_exact
first_pair_mismatch
first_right_exact
first_right_mismatch
target_order_informative_sites
target_highest_priority_exact
low_target_control_pair_exact
```

Rank distributions include:

```text
pair_rank:N
target_rank:N
```

A deliberately wrong control keeps the same first active ship but chooses the **lowest-priority** target first. This is not a mechanics proposal; it is a contrast to show whether the documented next-highest-priority target ordering is actually discriminating in the corpus.

## Evidence boundary

This is still not mutable queue replay.

The audit does **not** model:

- VCR outcome / survivor damage;
- destruction;
- capture and ownership mutation;
- second-pass repeated-pair combat;
- ship-to-planet continuation.

Therefore only the **first plain STANDARD VCR before any combat mutation** is compared.

If the exact-set multi-candidate population strongly matches the main selector and not the low-target control, promote that first-selection rule for its scoped population. Then proceed to mutable survivor/capture continuation using factual/replayed combat outcome state as the next differential boundary.

Any first-pair mismatch must be inspected before adding a canonical queue selector. Do not change existing static battle priority, pair eligibility, PIA/C&I, Galactic Power, matching-FC or repeated-pair rules merely to fit ordering residuals.