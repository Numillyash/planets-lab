# C5 Host combat — repeated-pair side population gate — pending runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains draft/open. Game `591478` is excluded from ordinary promotion.

## Why this gate exists

The successful factual queue differential on source:

```text
31509d2c9e9f4af89f80e5088597452d40f393c1
```

left only two resolved side mismatches:

```text
620917/T7/VCR6
621896/T25/VCR52
```

The targeted residual diagnostic proved that **both are the second occurrence of the same ship pair at the same battle-turn/location**. In each case the first encounter has the static higher-priority ship on RIGHT and the second encounter flips the pair.

Detailed runtime:

```text
docs/handoff/2026-09-09-combat-c5-factual-queue-runtime.md
```

## Documentation/evidence boundary

Primary Planets.nu documentation establishes that:

- complex stacked combat order can shift dynamically;
- each surviving ship proceeds through a target list;
- any two ships can fight each other a maximum of twice.

Secondary classic VGA Planets documentation describes the exact timeout/repeated-pair orientation rule: first-pass initiator is RIGHT; if the pair survives and fights again, the opposite ship becomes initiator/RIGHT.

Keep labels strict:

```text
maximum two fights / dynamic stack order: DOCUMENTED
exact second-pass side flip: secondary-supported, not primary DOCUMENTED yet
two observed residual flips: CORPUS_OBSERVED
```

## Committed population diagnostic — pending runtime

```text
tools/diagnostics/combat_host_repeated_pair_side_population_audit.py
tests/test_combat_host_repeated_pair_side_population_audit.py
```

Schema:

```text
planets-lab.combat-host-repeated-pair-side-population-audit.v1
```

The diagnostic scans all ordinary ship-vs-ship VCRs and groups identical ship pairs within one battle-turn/location.

It reports:

```text
repeated_pair_groups
repeated_pair_vcr_rows
occurrence_count
max_occurrences
over_documented_max_two_groups
stable_owner_groups
owner_change_groups
stable_owner_exactly_two_groups
stable_owner_exactly_two_side_flip
stable_owner_exactly_two_same_orientation
plain_static_comparable_groups
plain_static_first_right_exact
plain_static_first_right_mismatch
plain_static_second_reversed_exact
plain_static_second_reversed_mismatch
plain_static_two_pass_exact
plain_static_two_pass_mismatch
target_residual_groups
```

## Conservative plain-static subset

A repeated pair enters `plain_static_comparable` only when:

- exactly two factual VCRs exist for that pair at the site;
- ownership is stable across both VCRs;
- owner-current T-1 records align with factual owners;
- both standard priority keys are supported and distinct;
- neither ship has mission 7/20 targeted at the other member of this pair;
- no factual member is an Evil-Empire Gorbie (potential Galactic Power side override).

This intentionally excludes capture/ownership-change and obvious pre-standard/special-side confounders.

For that subset the expected two-pass pattern is:

```text
first VCR RIGHT  = static higher-priority ship (smaller standard key)
second VCR RIGHT = the opposite/static lower-priority ship
```

## Promotion rule

Promote a reusable repeated-pair side helper only if runtime shows a clean attributable population, ideally:

```text
over_documented_max_two_groups = 0
plain_static_two_pass_mismatch = 0
```

and the two former residual groups are ordinary examples of the same wider pattern.

If there are mismatches, inspect them before changing canonical static priority. Owner changes, capture/reinsertion, PIA/C&I and Galactic Power remain separate queue states.

Do not implement the full mutable target queue until this gate is understood.
