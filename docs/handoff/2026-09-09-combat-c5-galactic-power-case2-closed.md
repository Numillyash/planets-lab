# C5 Host combat — Galactic Power Case 2 closed — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains excluded from ordinary-mechanics tuning.

## Scope

This checkpoint closes former mission-7 residual Case 2:

```text
game 621896 / battle T28 / VCR67
LEFT  ship62 owner5 race8 hull70 Gorbie
      mission7 target38 PE2 FC001
RIGHT ship38 owner2 race2 hull23 T-Rex
      mission1 PE5 FCeqe damage24
```

It does not change Case 1 (`511506/T19/VCR13`), which remains a dynamic multi-ship eligibility / target-selection problem.

## Previously established differential

Matched-control runtime selected 41 structurally similar ordinary non-cloakable targeted-Intercept rows:

```text
40 canonical standard right-higher
 1 left-higher residual = exact Case 2
```

The target remained the only residual in exact `001`-vs-symbolic-nonKill and no-extra-T-survivor slices. Therefore a universal Intercept-side override was rejected.

The Gorbie boundary runtime then established:

```text
52 Gorbie appearances
48 Evil-Empire-owned
 4 non-Empire

Empire-owned Gorbie factual side:
  right: 29
  left:  19

standard relation:
  right_higher_priority: 41
  left_higher_priority:   7

forced-left override required:
  False: 41
  True:   7
```

The target is one of the seven rows where factual LEFT cannot be explained by canonical standard priority.

## Public game configuration — decisive target context

A corrected public Planets.nu API probe used:

```text
http://api.planets.nu/game/loadinfo?gameid=<id>
```

with HTTP 200 and valid JSON for all six ordinary Empire-Gorbie games.

For game `621896` the public response reports:

```text
game.id:               621896
game.name:             New Boston Sector
game.shortdescription: Standard Beginners
game.gametype:         2
game.maptype:          2
game.iscustom:         false
game.scenarioid:       0
settings.campaignmode: false
settings.maxadvantage: 500
race8 player id:       5
activeadvantages:      ""
```

The game description explicitly calls it a beginner game derived from Standard.

The same probe classified the six Gorbie games as:

```text
Classic:
  360690  Korvus Sector
  511506  Rambo 3 Sector
  620694  Ugo Sector

Standard Intermediate:
  621253  Virgo Pegasi Sector

Standard Beginners:
  621896  New Boston Sector
  680435  New Ireland Sector
```

The empty `activeadvantages` string is not an oracle for Standard built-ins: it is empty in Standard and Classic examples alike. Do not use it to negate documented Standard abilities.

## Primary documentation

Primary Planets.nu references:

```text
https://help.planets.nu/adv-galactic-power
https://help.planets.nu/variant-details
https://help.planets.nu/RaceSheetPlus
```

They establish:

- Galactic Power makes an Evil-Empire-owned Gorbie fight from the left;
- no special Mission or Friendly Code is required;
- the dedicated advantage page says it is active in all new Standard games;
- the Game Types table explicitly lists `Galactic Power = Yes` for **Beginner** and **Standard**, and `No` for **Classic**.

Therefore `Standard Beginners` is sufficient effective-enable context for the target even though `activeadvantages` is empty.

## Case 2 conclusion

The target has the exact documented race/hull identity and occurs in a public game type where Galactic Power is documented active. Its factual side is LEFT even though the canonical standard priority relation is `left_higher_priority`, so a forced-left exception is mechanically required.

The documented Galactic Power rule explains that differential without changing Intercept semantics, Friendly Code parsing, diplomacy, or standard battle priority.

Scoped evidence status:

```text
Galactic Power rule:                         DOCUMENTED
Beginner/Standard enablement:                DOCUMENTED
621896 public game type = Standard Beginners: PUBLIC_API_OBSERVED
Case2 race8/hull70/factual LEFT:             CORPUS_OBSERVED
Case2 standard relation requires override:   CORPUS_OBSERVED
fail-closed Galactic Power primitive:        TESTED
Case2 Galactic Power attribution:            DIFF_VERIFIED
```

`PUBLIC_API_OBSERVED` is descriptive provenance for the handoff; the project-wide canonical evidence labels remain `DOCUMENTED / CORPUS_OBSERVED / INFERRED / TESTED / DIFF_VERIFIED`.

## Canonical primitive boundary

`src/planets_lab/rules/combat/order.py::galactic_power_forces_left(...)` remains correct as a tri-state primitive:

- non-Empire or non-Gorbie -> `False`;
- Empire Gorbie + enabled -> `True`;
- Empire Gorbie + disabled -> `False`;
- Empire Gorbie + unknown enablement -> `None`.

Do **not** simplify this to `race8 + hull70 => LEFT`; Classic and Campaign/custom contexts remain different. The public game type/settings layer must resolve effective enablement before the Host side layer invokes the primitive.

## Immediate next work

Case 2 is closed. Return to Case 1:

```text
511506 / T19 / VCR13
```

That site has one factual VCR but a larger physical stack including Firecloud80, Meteors29/89/102 and ship73. Reconstruct dynamic engagement eligibility / opponent selection / cloak-state transitions there rather than treating the VCR as a two-ship priority residual.

After Case 1, continue with matching-FC / Harmonic Weapon Modulation boundaries, dynamic PIA/C&I selection, capture/reinsertion, and the ship-to-planet phase boundary.
