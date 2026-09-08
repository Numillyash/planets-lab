# C5 Host combat — Galactic Power corpus runtime boundary — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains excluded from ordinary-mechanics tuning.

## User-operated runtime

The user updated local `/root/projects/planets-lab` to:

```text
c88ade4604b3afd88b095af6ec1ec34a819ae933
```

and successfully ran:

```text
tests/test_combat_order.py
tests/test_combat_host_galactic_power_audit.py
tools/diagnostics/combat_host_galactic_power_audit.py
```

Runtime result:

```text
targeted tests: 27 passed
archives_considered: 11
payload_conflicts: 0
gorbie_appearances: 52
empire_gorbie_appearances: 48
nonempire_gorbie_appearances: 4
dual_empire_gorbie_appearances: 0
target_case_rows: 1
empire_gorbie_side:
  right: 29
  left:  19
nonempire_gorbie_side:
  right: 4
empire_gorbie_standard_relation:
  right_higher_priority: 41
  left_higher_priority:   7
empire_gorbie_forced_left_override_needed:
  False: 41
  True:   7
empire_gorbie_games:
  511506: 15
  620694: 14
  360690: 11
  621253:  5
  680435:  2
  621896:  1
tests rc=0; audit rc=0
artifact dir: artifacts/combat-c5-galactic-power-20260909-005706
```

Historical rows are `CORPUS_OBSERVED`; the primitive regressions are `TESTED`. The runtime does **not** justify a `DIFF_VERIFIED` promotion for Galactic Power because effective advantage enablement is not exposed in the prepared/archive fields audited here.

## Important correction — owner race + hull is not enough

Primary Planets.nu documentation states that the Galactic Power advantage forces an Evil-Empire-owned Gorbie to fight from the left when the advantage is active. The corpus boundary shows why the canonical helper must remain explicitly gated by effective advantage state:

```text
48 Evil-Empire-owned Gorbie ship-vs-ship appearances
19 factual LEFT
29 factual RIGHT
```

Therefore neither:

```text
owner race 8 + hull70 => LEFT
```

nor:

```text
ordinary game + owner race8 + hull70 => Galactic Power enabled
```

is supported by this corpus.

The 29 factual-right appearances are direct evidence that the six-game corpus mixes contexts where Galactic Power is not effective (for example Classic or Campaign/Custom with the advantage disabled), unless some independently documented stronger exception is later found. No such stronger exception is inferred here.

The audit found:

```text
game_context: {}
owner_activeadvantages_observed: []
```

for the displayed rows, including the target. The prepared/archive mechanics layer used by the audit therefore cannot establish advantage enablement.

## Correct interpretation of the seven override-required rows

The C5 standard side invariant is evaluated on already factual VCR sides: in ordinary standard ordering, the higher-priority combatant appears on the **right**. Thus:

```text
standard_relation = right_higher_priority
```

is standard-consistent, while:

```text
standard_relation = left_higher_priority
```

means the factual left combatant had the higher standard key and some pre-standard/special side mechanic is required.

Among the 48 Evil-Empire Gorbie appearances:

```text
41 standard_relation=right_higher_priority
 7 standard_relation=left_higher_priority
```

The seven `forced_left_override_needed=True` rows are precisely the useful Galactic-Power attribution candidates: an Evil Empire Gorbie is factual LEFT even though its own standard priority would otherwise have placed it on the RIGHT.

The other 12 factual-left Gorbie appearances do not independently prove Galactic Power, because standard ordering already places the Gorbie left in those rows.

The 29 factual-right Empire Gorbie appearances are incompatible with an active unconditional forced-left Galactic Power effect and therefore require disabled/not-applicable advantage context.

## Target Case 2 remains a strong Galactic-Power attribution candidate, but not yet closed

Target:

```text
game 621896 / battle T28 / VCR67
ship62 owner5 race8 hull70 Gorbie
factual side: LEFT
standard relation: left_higher_priority
forced_left_override_needed: True
```

So the target is one of the seven rows where a forced-left override is actually required. This removes the earlier Intercept hypothesis and makes documented Galactic Power the leading specific explanation.

However, the same target also has:

```text
game_context: {}
owner_activeadvantages_observed: []
```

Therefore the current corpus alone does not prove that Galactic Power was enabled in game `621896`. Do not close Case 2 or promote `DIFF_VERIFIED` until game configuration is independently resolved.

## Negative controls

Four non-Evil-Empire/captured Gorbie appearances were found, all factual RIGHT:

```text
nonempire_gorbie_side:
  right: 4
```

They correctly remain outside the Galactic Power primitive. No dual-Evil-Empire-Gorbie VCR was observed, so that ordering ambiguity remains fail-closed.

## Canonical primitive status

`src/planets_lab/rules/combat/order.py` contains:

```text
EVIL_EMPIRE_RACE_ID = 8
GORBIE_HULL_ID = 70
galactic_power_forces_left(...)
```

The helper is intentionally tri-state for the relevant race/hull:

- known non-Empire owner or non-Gorbie hull -> `False`;
- Empire Gorbie + explicitly disabled Galactic Power -> `False`;
- Empire Gorbie + explicitly enabled Galactic Power -> `True`;
- Empire Gorbie + unknown effective advantage state -> `None`.

This fail-closed shape is now `TESTED` by the successful user runtime. It must not be widened based on race/hull alone.

## Immediate next gate — public game configuration

The Planets.nu `/game/loadinfo` API is public and documented to return game/settings/player metadata, including `settings.campaignmode` and player `activeadvantages` when exposed.

Query exactly the six ordinary games containing Evil Empire Gorbie appearances:

```text
360690
511506
620694
621253
621896
680435
```

For each game capture at minimum:

```text
game.id
game.name
game.shortdescription
game.gametype
game.maptype
game.iscustom
game.scenarioid
settings.campaignmode
settings.maxadvantage
race8 player id
race8 player activeadvantages
```

The decisive target question is whether game `621896` is Standard with Galactic Power automatically active, or Campaign/Classic/Custom with a separately resolvable advantage configuration.

Do not infer enablement from `campaignmode=false` alone: Classic and Standard share broad API game-type buckets. Use `shortdescription` / explicit public metadata together with any exposed player advantage state.

## Evidence status after this runtime

```text
Galactic Power rule text:                         DOCUMENTED
fail-closed Galactic Power primitive:             TESTED
48 Empire-owned Gorbie appearances:               CORPUS_OBSERVED
29 Empire Gorbie factual RIGHT:                   CORPUS_OBSERVED
19 Empire Gorbie factual LEFT:                    CORPUS_OBSERVED
7 rows requiring a forced-left override:          CORPUS_OBSERVED
4 non-Empire Gorbie factual RIGHT controls:       CORPUS_OBSERVED
Case2 race8/hull70/LEFT/override-needed identity: CORPUS_OBSERVED
Case2 Galactic Power effective enablement:        OPEN
Galactic Power DIFF_VERIFIED:                     NOT YET
```

## After public configuration resolution

- If game `621896` is proven to have Galactic Power enabled, close Case 2 as the documented forced-left exception and integrate it into the Host side-assignment layer with explicit advantage state.
- If Galactic Power is proven disabled there, the attribution is rejected and Case 2 remains open for a different special-side mechanic.
- Independently classify the other five games so factual-right Empire Gorbies are no longer treated as contradictory mixed context.
- Then return to Case 1 dynamic multi-ship opponent selection / cloak eligibility.
