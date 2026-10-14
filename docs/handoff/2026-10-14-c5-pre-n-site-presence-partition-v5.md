# Ordinary C5 — prior-site history vs T−1 arrival uncertainty V5

Date: 2026-10-14. Canonical repository: `Numillyash/planets-lab`, branch `main`.
Research-only. Horwasp remains parked; PR #28 remains draft/open.

## Frozen V4 runtime confirmed

`runtime-logs/combat-c5-parent-queue-arrival-uncertainty-v4/20261014T122122Z_cb69a22be295`

Source main `cb69a22be295bd17103fadf606c8869252d1bf52`,
exit_code 0, committed evidence, SHA256-pinned public100 DB read-only.

V4: 27 ordinary ship-only sites / 63 adjacent transitions / 56 examined,
7 unavailable; 25 conditional V2 NO_PAIR: 17 with possible T−1 unresolved
arrivals, 8 without indexed witnesses. V4 makes zero new pair predictions
and does not prove Host queue exhaustion.

**Recount from immutable V4 report**: 219 witness *appearances* across the
56 analyzed transitions but 54 unique (game,turn,site,ship) combinations;
within the 25 NO_PAIR transitions, 157 appearances but only 45 unique
site-ship combinations, across 12 sites (8 with witnesses). Sources within
NO_PAIR deduplicated by site-ship: normal_mine_route_risk 17,
tow_attempt 13, tow_target 9, sphere_topology_not_integrated 3,
pre_move_mkt_mass_change 3. Repeated transitions are not independent
ships or independent games.

## V5 experimental question

V4's "potential arrival" list may contain a ship which has ALREADY fought at
that same site in an earlier VCR. That is **not** a newly observed arrival
between battles; whether that ship survived, was captured or remains eligible
is nevertheless unresolved without independent terminal state. V5 separates:

- `PRIOR_SAME_SITE_VCR_PARTICIPANT_CARRY_UNRESOLVED`: candidate ship ID is
  present in factual site history STRICTLY BEFORE current VCR N.
- `NOT_SEEN_IN_PRIOR_SITE_VCR_TMINUS1_ARRIVAL_UNRESOLVED`: no such earlier
  factual site VCR record exists. Absence of combat history does not prove
  physical arrival or next-battle eligibility.

This categorization uses the immutable V4 report Git blob
`847d0a951c1a3bdddc55f1b1b9a82f9d50c0c610`, frozen site census blob
`fda92475988d2f7dfbc7b93606de4f8cec909806`, and original current/prior
VCR ship IDs from the read-only public100 DB. Site/game/turn preselection
is frozen; no future N+1 VCR payload is accessed for classification.
The DB reader may materialize whole turns, but the classifier reads only
prefix IDs <= current N. N+1 identities and masses are not operands.

Counts deduplicate at site-ship rather than improperly summing repeated
transition witness appearances; per-transition temporal classes remain
available. Zero new battles, queue promotions or position predictions.
No changes to the canonical combat executor, source DB `CURRENT`,
`planets-intel`, RNG, Shield Generator or Horwasp.

## Runtime command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-pre-n-site-presence-partition-v5-with-evidence.sh
```

Report:
`artifacts/combat/c5-pre-n-site-presence-partition-v5/published/report.json`.

Evidence:
`runtime-logs/combat-c5-pre-n-site-presence-partition-v5/`.

## Acceptance and next decision

V5 must preserve 27/63/56/7 and all 25 original NO_PAIR identities,
with 219 original appearances and **zero** newly claimed Host predictions.
After real runtime, compare the counts of NO_PAIR outcomes that have only
earlier-site participants vs genuinely unseen-in-prior-VCR witnesses.
For unseen T−1 ship cohorts, select independently modelled movement
(Tow, mine, interception) without importing future N+1 ship positions.
For prior-site participants, require independent terminal carry/eligibility
before changing the parent queue. Neither path may promote from retrospective
classification alone.
