# Combat C4 checkpoint — planet sequence differential

Date: 2026-09-07

This checkpoint records the C4 historical differential evidence for repeated same-turn ship-vs-planet/starbase engagements.

GitHub is the source of truth.

```text
C4 branch                     agent/combat-c4-planet-sequences
PR                            #27
planets-intel source HEAD     7211ee1a94c2a712739410283429507cc227368b
mechanics/runtime HEAD        70ab14cfad8aa7676489df34a71ca9cbd724fd79
post-main-sync branch HEAD    2b9beff633e1f773ba66fd699cfff0df3aee364f
main merged into C4           1945e81fd14baa0df7c9cf077ece5aef8812cb65
```

## Scope

C4 adds a pure planet/starbase sequence layer in:

```text
src/planets_lab/rules/combat/planet.py
```

and an independent historical differential in:

```text
tools/diagnostics/combat_planet_chain_audit.py
```

The source implementation was inventoried from current `planets-intel/feature/operational-ui`, but imported formulas were treated as candidates until rechecked against the raw `planets-lab` corpus.

C4 does **not** implement Host opponent selection, battle queues, diplomacy/PE/mission rules, ownership transfer, or full planet-phase orchestration.

## Corpus

Final runtime gate after the native planet beam-tech rounding correction:

```text
archives                         12
raw_vcr_observations          22256
unique_vcrs                    6469
payload_conflicts                 0
replay_supported               6469
planet_appearances             3719
candidate_same_turn_planet_chains 110
same_location_transitions       136
```

All repeated planet chains in this corpus have VCR gap `1`.

## Ordinary population

Excluding special/campaign/Horwasp-heavy game `591478`:

```text
ordinary transitions      103
match                     102
not_comparable              1
mismatch                    0

starbase transitions       92
no-starbase transitions    11

shield carry match        103 / 103
shield carry mismatch       0
```

### Starbase shield carry

All 92 ordinary repeated starbase defenders preserve the replay terminal shield value into the next factual VCR start:

```text
92 / 92 exact
```

This is independent next-VCR differential evidence for between-attacker shield persistence.

It does **not** establish the hidden post-damage starbase defense / beam-tech / accumulated-base-damage split.

## Plain-planet exact path

Exact no-starbase reconstruction is attempted only when factual VCR state explicitly has:

```text
hasstarbase = false
```

The candidate persistent planet defense is inferred from factual combat mass:

```text
planet_defense = mass - 100
```

The inferred state must first reproduce the factual start combatant before it is allowed into the carry-over oracle.

The carry model then applies:

```text
next_dp = dp - TRUNC(dp * battle_damage / 100)
next_dp -= lost_generated_planet_fighters
next_shield = replay_terminal_shield
battle damage resets for the next engagement
```

and re-derives planet beams, bays, fighter count, mass and native beam tech.

Final ordinary no-starbase result:

```text
transitions                       11
exact carry match                 10
start reconstruction mismatch      1
next-state exact mismatch          0
shield carry match                11 / 11
```

The ten comparable rows reproduce the complete next factual combatant with no mismatch fields.

Evidence status for the supported ordinary plain-planet sequence path:

```text
CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

## Native planet beam-tech correction

The imported implementation originally used a truncating square-root mapping for native planet beam tech. The first C4 corpus gate exposed six ordinary no-starbase rows whose only differing field was `beamid`, always with factual beam tech one level above the imported value.

The candidate was corrected to integer nearest rounding of:

```text
ROUND(SQRT(DP / 2))
```

capped to tech 1..10 for positive DP.

After this correction:

```text
ordinary no-starbase exact matches     5 -> 10
ordinary exact next-state mismatches   1 -> 0
ordinary start reconstruction mismatch 5 -> 1
```

Threshold regression tests were added around the observed/documented beam-tech steps.

## Remaining ordinary no-starbase row

The sole remaining `not_comparable` row is:

```text
game   621253
turn   26
planet 113
VCR    111 -> 112
```

Before the beam-tech correction it differed only as:

```text
predicted beamid = 0
factual beamid   = 1
```

Every other projected field matched, including `beamcount`.

`rebuild_planet_combatant()` emits `beamid=0` only when the derived beam count is zero. Therefore this row is an inactive-weapon metadata difference on a zero-beam planet, not evidence against the DP/fighter/shield carry model. The audit remains deliberately strict and leaves the row `not_comparable` instead of weakening field comparison globally.

## Starbase hidden-state boundary

C4 retains the source fail-closed boundary for a surviving starbase that receives non-zero planet hull damage.

A VCR does not uniquely expose enough persistent state to recover all of:

```text
starbase defense
starbase beam tech
starbase accumulated damage
```

Therefore the simulator must not invent this split.

Supported exact starbase mechanics remain limited to states where required persistent inputs are known and the hidden damaged-base branch is not entered. Starbase shield persistence has independent corpus evidence; the hidden post-damage defense split does not.

Evidence labels:

```text
ordinary starbase shield persistence:
    CORPUS_OBSERVED + TESTED + DIFF_VERIFIED

starbase zero-hull-damage carry helper:
    TESTED

surviving starbase + nonzero hull damage:
    FAIL CLOSED / unresolved
```

## Special game 591478

Game `591478` remains isolated from ordinary promotion.

Final C4 population:

```text
transitions                   33
match                         17
not_comparable                 9
mismatch                       4
reappearance_after_defeat      3

starbase                      17
no-starbase                   16
shield match                  28
shield mismatch                2
```

Its residuals include multiple combat-state fields and remain a special/campaign/Horwasp research bucket rather than evidence for changing ordinary Classic planet rules.

## C4 closure boundary

C4 closes the currently attributable ordinary repeated-planet persistence layer:

- replay terminal shield -> next planet/base engagement shield;
- plain-planet defense-post damage carry;
- generated planetary fighter losses reducing DP;
- re-derived plain-planet combatant state;
- corrected native planet beam-tech rounding;
- explicit fail-closed handling of hidden damaged-starbase persistence.

C4 does **not** close:

- between-phase ship repair before planet combat;
- complete starbase post-hull-damage persistent state;
- planet/base capture orchestration;
- Host engagement eligibility and battle ordering;
- PE/mission/diplomacy and multi-player queues;
- game `591478` special sequence behavior.

The next combat milestone should move to the missing Host combat phase rather than broadening C4 with unsupported starbase assumptions.
