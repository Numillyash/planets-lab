# Combat C3 checkpoint — ship sequence carry-over diff verified

Date: 2026-09-07

This checkpoint records the completed C3 historical differential evidence for ordinary NuHost Classic ship battle sequences.

GitHub is the source of truth. At the final mechanics/runtime gate:

```text
base main before merge = aef6d652b1f7f59173283dd7c0e0aa3f0e1d6bb9
C3 branch              = agent/combat-c3-sequences
mechanics/runtime HEAD = afe79bd924dd87ff36802e1ed516d7cfd91f0e93
PR                     = #26
```

## Scope completed in C3

- Added pure ship battle-sequence carry-over rules in `src/planets_lab/rules/combat/sequence.py`.
- Carried `shield`, `damage`, `crew`, `torpedoes`, and `fighters` across explicit engagements.
- Recomputed damage-limited effective beams, launchers, and bays.
- Kept Federation and Lizard behavior behind explicit sequence inputs rather than inferring advantages inside generic helpers.
- Added read-only historical same-turn/same-location chain differential tooling over cached loadall archives.
- Added phase-aware classification for `ship_vs_ship -> ship_vs_ship` versus `ship_vs_ship -> ship_vs_planet` transitions.
- Separated capture continuation from true destroyed reappearance.
- Preserved the C2 fail-closed VCR replay boundary and raw archive immutability.

## Corpus baseline

Final C3 run uses the same 12 cached loadall archives as C2:

```text
archives                    12
raw_vcr_observations      22256
unique_vcrs                6469
payload_conflicts             0
replay_supported           6469
ship_appearances           9219
candidate_ship_turn_chains 1015
same_location_transitions  1485
metadata_conflicts            0
```

Phase distribution:

```text
ship_vs_ship -> ship_vs_ship      938
ship_vs_ship -> ship_vs_planet    544
ship_vs_planet -> ship_vs_planet    3
```

Terminal classification:

```text
survived   1431
captured     25
destroyed    29
```

All 25 captured reappearances change owner. The 29 true destroyed reappearances are confined to the special/campaign/Horwasp-heavy game `591478`; none occur in the ordinary 11-game subset.

## Federation between-fight shield recovery

The original imported candidate interpreted Federation recovery as 25% of missing shields. Historical chains reject that formulation.

The 48 race-1 transitions are instead explained by fixed recovery of up to 25 shield points, capped by the damage-reduced maximum shield:

```text
next_shield = min(100 - damage, shield + 25)
```

Observed examples include:

```text
0  -> 25
40 -> 65
55 -> 80
65 -> 90
79 -> 100
80 -> 100
84 -> 100
88 -> 100
```

Damage caps also explain observed `0 -> 17` and `0 -> 4` transitions.

Final race-1 shield accounting:

```text
transitions               48
exact/both                28
federation_candidate      20
shield mismatches           0
```

Evidence status for this scoped rule:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Exact-zero shield crew correction

C3 exposed a Python-port semantic difference from upstream c2ng `HostAlgorithm::hit()`.

Upstream applies crew damage by checking the participant's stored shield state before the final new shield value is assigned. Therefore a hit that changes a positive shield value exactly to zero does not inflict crew damage on that same hit; crew damage begins on a subsequent hit, or on a hit that actually overflows through shields.

The first Python port checked the newly computed local shield value and incorrectly applied crew loss on exact-zero depletion.

After correcting Nu replay ordering to match upstream c2ng and adding regression tests, all ordinary ship-to-ship survivor residuals disappear.

## Strong differential result

Ordinary games, surviving ship, same location, `ship_vs_ship -> ship_vs_ship`:

```text
transitions    764
match          764
mismatch         0
```

Per-field differential:

```text
damage      764 / 764 exact
crew        764 / 764 exact
torpedoes   764 / 764 exact
fighters    764 / 764 exact
shield      764 / 764 explained by exact carry or scoped Federation recovery
```

The strongest globally adjacent VCR subset is also perfect:

```text
ship_vs_ship survivor, VCR gap = 1
transitions    751
match          751
mismatch         0

damage      751 / 751 exact
crew        751 / 751 exact
torpedoes   751 / 751 exact
fighters    751 / 751 exact
```

This is an independent next-VCR oracle: the simulated terminal state of factual VCR N is compared with the factual starting state of the same surviving ship in the next eligible VCR.

Evidence status for ordinary Classic ship battle sequence carry-over:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Phase-boundary residual is not a C3 carry failure

In the ordinary 11-game subset after the exact-zero correction:

```text
ordinary_all
transitions                 1169
match                       1138
reappearance_after_capture    23
mismatch                       8
```

All eight remaining mismatches are damage-only and occur on the `ship_vs_ship -> ship_vs_planet` boundary:

```text
ordinary_ship_to_planet_boundary
transitions                  397
match                        374
reappearance_after_capture    15
mismatch                       8
problem signature         damage
```

At that Host phase boundary a separate repair step may intervene. Crew, torpedoes, fighters, and shield semantics are otherwise clean in this ordinary boundary population. These eight rows are therefore not evidence against same-phase ship battle carry-over and should be handled in C4/Host phase reconstruction rather than by modifying the Classic resolver.

## Special game 591478

Game `591478` remains a separate special/campaign/Horwasp-heavy evidence bucket. It contains all 29 `destroyed -> reappeared` transitions and most of the broad multi-field sequence irregularities seen before phase-aware scoping.

Do not generalize ordinary Classic carry-over rules to explain those special transitions. They require separate race/campaign/special-mechanics work.

## C3 conclusion

C3 closes ordinary Classic ship battle sequence carry-over for the current historical corpus:

- deterministic pairwise replay remains 6469/6469 supported;
- ordinary same-phase surviving ship chains are 764/764 differential matches;
- strongest adjacent-VCR subset is 751/751;
- damage, crew, torpedoes, fighters all carry exactly in that scope;
- Federation between-fight recovery is fixed `+25` shield points capped by `100-damage`;
- capture continuation is valid and changes owner;
- true destroyed reappearance is special-game-only in this corpus;
- ship-to-planet phase-boundary repair is explicitly excluded from the strict same-phase carry oracle.

## Next phase — C4 planet/starbase sequences

C4 should proceed from the merged C3 `main` and focus on planet/starbase combat persistence rather than reopening ordinary ship carry-over.

Required work:

1. reconstruct consecutive ship-vs-planet/starbase battles at the same planet in factual VCR order;
2. distinguish plain planet defense from starbase defense;
3. determine what planet/base combat state persists between attackers and what resets;
4. verify ship state entering the planet phase, including documented between-phase repair;
5. preserve the surviving-damaged-base fail-closed boundary when exact persistent defense split is not recoverable;
6. compare simulated terminal planet/base state against the next factual planet VCR wherever an independent oracle exists;
7. keep game `591478` special mechanics separately labeled rather than forcing them into ordinary Classic rules;
8. only after C4 move to Host engagement eligibility/order/side assignment and diplomacy/PE/mission interaction.
