# Ordinary C5 pre-N T−1 site ingress versus residence — V6

Mainline repository `Numillyash/planets-lab`; branch `main`, 2026-10-14.
Observational research; no production combat-executor, `CURRENT`, or
`planets-intel` changes. Keep existing draft PR #28 draft/open.

## Immutable V5 runtime success

`runtime-logs/combat-c5-pre-n-site-presence-partition-v5/20261014T124048Z_b6af6f4b3e51`

Verified in GitHub: exit_code=0, original source commit
`b6af6f4b3e51904962158dde5d526984e3294c29`.
Pinned published V5 Git blob:
`bd293c573c85bd849c9e6add06af661bfe519ee9`.
Pinned V4 Git blob:
`847d0a951c1a3bdddc55f1b1b9a82f9d50c0c610`.

V5: 27 frozen sites, 63 adjacent transitions, 56 evaluated, 7 without
context, 25 NO_PAIR; 16 transitions have candidate ships not previously
seen in the site VCR prefix, one only prior-site participants, eight with
no indexed witness. Across NO_PAIR, 157 witness appearances: 50 earlier-
site participation appearances and 107 unseen-in-prefix appearances.
These are repeated observations, not independently verified arrivals.

## V6 scientific discriminator

V5's `UNSEEN` is absence of earlier *combat*, not evidence of a newly
arrived ship. The V4 source also captures independent T−1 site geometry:

- `start_at_site=True`: original owner T−1 ship physically at the
  current site's coordinates in archived start state. Departure/remaining
  at site is UNKNOWN, so do not infer N site membership.
- `waypoint_at_site=True, start_at_site=False`: independent T−1
  destination request points at current site. It does NOT prove the ship
  reached the site when Tow, foreign mines, limited fuel, sphere,
  special movement or interception may intervene.
- `start_at_site=True, waypoint_at_site=True`: both source facts.
- If a ship is present in a preceding same-site VCR, prior-battle
  carry/terminal status must remain unresolved.

Direct read-only source join gives, within 107 V5 NO_PAIR
unseen-in-prior-VCR appearances: 12 start-only, 83 waypoint-only,
12 start-and-waypoint. These represent 42 unique (game,turn,site,ship)
identities: 12 start-only, 18 waypoint-only, 12 both.
In particular, 78/107 appearances are concentrated in G421276/T115;
neither appearance count nor 16 NO_PAIR transitions are independent
mechanics replications.

The new V6 report calculates this division from byte-pinned V4/V5
and revalidates every observed transition, VCR-prefix class, ship ID,
owner, source, nonleakage flag, pair denominator, no-prediction claim
and site membership before publishing. It uses no DuckDB access:
the source evidence already contains all required T−1 and pre-N facts.

A remaining waypoint-only witness means arrival is still uncertain,
not that a prospective new combat pair is eligible. A start-only witness
means possible site residence or departure, not demonstrated movement
to the site. Empty witness lists never prove full Host site exhaustion.

## Runtime

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-tminus1-site-ingress-residence-v6-with-evidence.sh
```

Report: `artifacts/combat/c5-tminus1-site-ingress-residence-v6/published/report.json`.
Evidence: `runtime-logs/combat-c5-tminus1-site-ingress-residence-v6/`.

Next experimental research on the actual source of uncertainty should
prioritize independently verifiable normal-mine route and Tow/movement
replay, with source-specific positive/negative controls, while keeping
unknown mine hits, sphere geometry and terminal state fail-closed.
Do not treat this retrospective source classification as a generative
NuHost predictor. Full Host queue prediction remains blocked.
