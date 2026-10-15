# C5 V18 — G467386 25 LY anomaly and owner-current archive visibility

Canonical repo: Numillyash/planets-lab on `main`. Keep PR #28 draft.
Never modify production `planets-intel`, corpus CURRENT, the
combat executor, or the external-engine branch.

## V17 successful server evidence

`runtime-logs/combat-c5-disjoint-discriminative-chunnel-gates-v17/20261015T121037Z_59dd897f5a79`
with exit_code 0; source
`59dd897f5a79b96c030e715f3fecd676f818131e`, pinned
report Git blob `a6256b70dc63b9b7126a211245bc65ce20ece863`.

Metadata-selected 16 game-disjoint public100 games, 48 T−1/T
windows, 113 stock Firecloud candidate edges, no missing contexts.
98 positive T−1 fully gated edges: 84 observed actors at distinct
target, 13 owner-current T unavailable, ONE owner drift.
All 14 abstentions are concentrated in TWO windows:
- G227887 / T72: 13 missing owner-current T actors, all owner #6,
  targeting same Firecloud #182, whose T record has owner drift.
- G338264 / T50: 1 owner-drift actor.
These are NOT 14 independent movement failures, nor can stale
foreign-perspective sightings prove their final positions.

15 T−1 single-failed-gate negatives: 9 co-located
source=target (explicitly NON_DISCRIMINATIVE); six truly
geometrically distinct. Of those six, four stayed at source,
one ended elsewhere, one at original target.
Last case:
**G467386 T75 Firecloud #467 -> #80**:
T−1 initiator at (1141,1459), target at (1126,1439), separation
25 LY, T actor and target both at (1126,1439), actor net fuel
delta 48 KT (not exactly 50). Conventional Warp Chunnel minimum
distance per https://help.planets.nu/mis-warp-chunnel is 100 LY.
This is a real post-Host short-distance endpoint anomaly requiring
phase attribution; NOT a proven sub-100-LY Chunnel. Possibilities
include transport via another mechanism, tow interactions, archive
projection limitations, T−1/T phase transitions, or modified rules;
none is presently established.

## V18 exact post-hoc inventory

Byte-pin V17 report and immutable public100 database, preserve 48/113
and exact case identities of all 14 abstaining positives plus 6
geometrically discriminative negatives (20 cases). NO reselection.
For the affected game/turn windows freeze exact T−1 owner-current
actor/target ID, position, numeric code identity, waypoint,
mission, Warp, fuel, damage, nearby ship stack, and raw Tow
REQUEST identities. No raw friendly codes or private messages
in output; Tow request is not proven successful tow lock.

**Only after all T−1 windows have frozen**, reread post-Host T
owner-current states and exact T archive perspectives. Record
whether the original owner has any T perspective, whether each
actor/target has a fresh current ship record versus stale contact
only, and any fresh *reported* owners. A fresh foreign observer
record is NOT automatically owner-current authoritative. Do
not interpret ship absence as destruction or conclude owner
transfer without independent phase evidence.

Independently reproduce all 20 V17 actor outcomes and net fuel
deltas. Report the count of positive-abstention missing-owner
perspectives by game/turn (not 13 independent errors).
Inspect G467386/T75 coordinates, original mission/waypoint,
Tow REQUESTS and nearby ships without assigning cause.

## One server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-short-chunnel-and-visibility-audit-v18-with-evidence.sh
```

Report:
`artifacts/combat/c5-short-chunnel-and-visibility-audit-v18/published/report.json`.
Evidence:
`runtime-logs/combat-c5-short-chunnel-and-visibility-audit-v18/`.

## Future

Pending V18, test whether apparent G467386 short-distance travel
can be explained by a known T−1 movement pathway without
asserting a Chunnel distance exception; examine complete
time-indexed movement, tow lock and owner-current visibility.
For causal Chunnel activation validation, acquire a NEW frozen
corpus generation and prospective game-disjoint outcomes beyond
the repeatedly explored public100. Until then retain strict
research-only abstention.
