# Finite-fuel Tow same-line context-resolution runtime — 2026-09-11

Runtime source:

- candidate: `c0f954cf5a3c3c44e006268001f61bcaf22974a2`
- source gate: `logs/finite-fuel-tow-same-line-stop-context-20260911T091457Z-ab01248c-25714`
- collected gate: `logs/finite-fuel-tow-same-line-context-resolution-20260911T123937Z-c0f954cf-11500`

All stages completed `0/0`.

The three previously unexplained same-line rows split cleanly:

```text
cases=3
bounded_web_damage_context_rows=2
unresolved_damage_context_rows=0
alchemy_rows=1
alchemy_exact_cargo_signature_rows=1
alchemy_full_conversion_hypothesis_rows=1
alchemy_adjusted_envelope_possible_rows=1
alchemy_adjusted_snapshot_exact_rows=1
```

`360690/T44` and `360690/T185` each show exactly one web-damage quantum on the tower together with a visible hostile web crossing and factual endpoint containment. They are bounded web-context confounders for finite-fuel Tow evidence. This does not reconstruct the random web-hit location and does not promote new mine mechanics.

`360690/T41` has no visible mine/web or tower-damage lead. Its towed target `353`, hull `105`, has the Alchemy special `Converts 3 supplies to 1 mineral`. The observed cargo transition is exact:

```text
supplies: 2700 -> 0
minerals total: 0 -> 900
candidate non-fuel mass reduction: 1800 KT
target non-fuel mass: 3628 -> 1828 KT
```

Applying that exact full-conversion mass reduction before the Tow fuel calculation changes the snapshot combined movement mass to `2163 KT`. With tower snapshot fuel `124 KT`, the existing proportional fuel model requires `131 KT` and projects exactly to the factual endpoint `(2183, 2688)`. The bounded phase-fuel envelope also contains exact witnesses.

This runtime changes the next question from whether an Alchemy-adjusted mass can explain T41 to whether Host documentation and a historical differential establish the phase order and mass basis independently.

Official Planets.nu documentation supplies those candidate rule semantics:

- <https://help.planets.nu/fuel-details> says movement mass includes all mass of a starship being towed, that masses are checked after Alchemy, and that insufficient-fuel movement distance is prorated.
- <https://help.planets.nu/host-order> places Alchemy before the mass check and before towing ships move.

The next bounded gate must therefore verify T41 as a discriminator between:

1. pre-Alchemy combined mass;
2. post-Alchemy combined tower+towed mass;
3. post-Alchemy tower-only mass.

Until that gate is runtime-verified, finite-fuel Tow remains **OPEN** and no `planets-intel` transfer is justified.
