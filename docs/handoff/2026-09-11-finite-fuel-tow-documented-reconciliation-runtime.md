# Finite-fuel Tow documented reconciliation runtime — 2026-09-11

Runtime source:

- candidate: `bc3b767330dc23ed09303eed766365fa53877209`
- source gate: `logs/finite-fuel-tow-same-line-context-resolution-20260911T123937Z-c0f954cf-11500`
- collected gate: `logs/finite-fuel-tow-documented-reconcile-20260911T160149Z-bc3b7673-29099`

All stages completed `0/0`.

## Historical discriminator

The cleaned finite-fuel Tow case is:

```text
game        360690
turn        41
tower       425
target      353
origin      (2159, 2741)
waypoint    (2184, 2685)
observed    (2183, 2688)
route       61.326992425847855 ly
fuel factor 8100
```

The towed target is an Alchemy ship. Its exact observed cargo transition is:

```text
supplies        2700 -> 0
mineral gain       0 -> 900
mass reduction       1800 KT
```

The gate compares three competing movement-mass models under the documented proportional insufficient-fuel rule:

```text
pre-Alchemy combined mass
  total mass      3963 KT
  fuel required    241 KT
  fuel available   124 KT
  endpoint         (2172, 2712)
  factual exact    no

post-Alchemy combined tower+towed mass
  total mass      2163 KT
  fuel required    131 KT
  fuel available   124 KT
  endpoint         (2183, 2688)
  factual exact    yes

post-Alchemy tower-only mass
  total mass       333 KT
  fuel required     20 KT
  fuel available   124 KT
  endpoint         (2184, 2685)
  factual exact    no
```

Runtime summary:

```text
cases=1
pre_alchemy_combined_exact=0
post_alchemy_combined_exact=1
post_alchemy_tower_only_exact=0
alchemy_mass_basis_discriminator=1
combined_mass_discriminator=1
```

This is an attributable historical discriminator: the factual endpoint selects post-Alchemy combined tower+towed mass and rejects both the pre-Alchemy combined-mass model and a tower-only movement-mass model.

## Documentation cross-check

Official Planets.nu documentation supplies the matching rule semantics:

- <https://help.planets.nu/fuel-details> documents that movement mass includes the entire towed ship and that insufficient-fuel movement distance is prorated;
- the same fuel documentation states that movement masses are checked after Alchemy;
- <https://help.planets.nu/host-order> places Alchemy before the movement-mass check and before towing ships move.

Scoped evidence status for the **base finite-fuel Tow movement rule** is therefore promoted to:

```text
DOCUMENTED + CORPUS_OBSERVED + TESTED + DIFF_VERIFIED
```

`TESTED` is scoped to the deterministic combined-mass Tow movement path and proportional insufficient-fuel movement regression. It does not assert an end-to-end Alchemy phase implementation where that phase is not yet modeled.

## Scope boundary

This promotion closes the base question of what mass and proportional fuel movement rule a successful finite-fuel Tow uses. It does **not** claim that all Tow behavior is reconstructed.

Still separate / fail-closed where unresolved:

- Tow contests, chains and cycles beyond the supported topology;
- random web/mine hit point reconstruction and its exact interaction with Tow;
- Chunnel, ion-storm and other external relocation interactions not independently attributable to the Tow fuel rule;
- exact full Host phase integration for Alchemy if the simulator pipeline has not yet modeled that phase;
- special/campaign/Horwasp behavior outside the ordinary Classic scope.

The two former same-line residuals `360690/T44` and `360690/T185` remain bounded hostile-web damage context, not Tow-fuel evidence.

## Roadmap consequence

Finite-fuel Tow is no longer a blocker inside the ordinary movement checkpoint. Movement can remain closed for broad residual hunting and be reopened only for bounded contradictions or explicitly scoped interaction work.

The immediate project focus remains the full Host combat phase: engagement eligibility, factual queues, opponent selection, side assignment, Priority Intercept / Primary Enemy / mission interactions, diplomacy and capture continuation.

No automatic `planets-intel` production transfer follows from this lab evidence promotion; production use must preserve the same evidence and scope boundaries.
