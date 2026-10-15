# C5 Firecloud V13 — pre-outcome, game-disjoint exposure study

Repository `Numillyash/planets-lab`, `main`. The external-engine
research branch, production `planets-intel`, combat executor and corpus
`CURRENT` remain untouched. PR #28 remains Draft/Open.

## Published evidence V12

Successful V12 evidence:
`runtime-logs/combat-c5-phase-aware-firecloud-v12/20261015T070244Z_07dac43baa86`.
Source `07dac43baa86e5aa2194fe7d0abed22a50a19d72`, exit_code=0.
Pinned V12 Git blob `3e6445db188fe7945133a0563605d114c93fbaba`.

13 original V9 residuals unchanged. Eight are retrospectively concordant
with three separate stock Firecloud source/target edges:
- G245123 T75 Firecloud 293 -> 646, 4 ship comparisons;
  observed actor and target at destination, actor fuel delta=50 KT.
- G306971 T116 Firecloud 377 -> 581, 3 ship comparisons;
  actor and target at destination, actor fuel delta=50 KT.
- G476826 T96 Firecloud 458 -> 340, 1 ship comparison;
  actor and target at destination, actor fuel delta=10 KT (NOT 50).
All three initiators have exact T−1 Warp 0. Multiple passenger records
at the same event are correlated; these are NOT eight independent
Chunnel executions. Official documentation says Chunnel costs
50 KT and takes place after ordinary movement:
https://help.planets.nu/mis-warp-chunnel
This is strong *posthoc* evidence, not proof of mechanism or
independent forecast validation.

## V13 preregistered experimental design

EXCLUDE all 17 C5 original V6 site games PLUS all 8 V9 movement
validation games. Source selection uses only public100
`source_members(game_id, archive_turn)` metadata: select 12 remaining
games evenly spaced by numerical game ID, and 3 adjacent windows at
1/4, 1/2 and 3/4 of their available window span (36 total).
No VCR, T position, target Chunnel event, battle outcome or mine
hit is used for sampling. This source cohort is independent of the
specific V9/V12 games but still uses the same previously studied
public100 corpus, so does NOT count as a new independent dataset.

For ALL 36 windows, compute exact independent T−1:
- Same-owner numeric-FC actor/target candidates, both stock
  Firecloud hull 56, initiator Warp 0/fuel>=50, target Warp0/fuel>0,
  distance >=100LY, no T−1 Tow request against either endpoint.
  Unknown custom abilities and active phases remain out of scope.
  Ambiguous duplicate numeric target ID fails closed.
- Independently reconstructed ordinary normal movement endpoints,
  using exact T−1 archive catalog/settings, which may abstain
  on unknown Sphere or conflicts.
- Positive conditional passenger exposure: same-owner vessel's
  independently calculated pre-Chunnel normal endpoint equals the
  stock Firecloud source, excluding actor and target IDs.
  Split passengers by mine-risk/no-indexed-mine-risk; risk exposure
  is a conditional no-hit endpoint, NOT actual presence.
- Negative model control: first ten stable ordinary normal movement
  forecasts per window ending away from all eligible actor sources
  and target destinations, selected before T, not observational
  proof of nontransport.

Freeze *all source graphs, passenger and negative cases* in memory
before ANY T archive read. Then independently compare owner-current T
ship positions. Report ship-level success/mismatch/abstain but group by
game and actor-target **episode**, never claim each passenger is an
independent replication. Actor T target position, target T position,
and fuel delta=50 are a supportive joint observational signature,
not certain proof of executed Chunnel, especially when intermediate
movement, fuel transfers, or combat can change the archive state.

If no eligible edges or passengers are found, V13 reports the zero
exposure and makes NO validation claim. Missing, shifted owner/hull,
unavailable T-1 catalog/settings, or unknown movement remains
explicitly `ABSTAIN`. No canonical movement rule or combat queue
promotion is authorized by this experiment.

## Run

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-firecloud-disjoint-validation-v13-with-evidence.sh
```

Output: `artifacts/combat/c5-firecloud-disjoint-validation-v13/published/report.json`.
Evidence: `runtime-logs/combat-c5-firecloud-disjoint-validation-v13/`.

Future: if genuine multi-game supportive T−1 Chunnel exposures survive,
develop broader, owner-current archive phase matching including
Chunnel-blocking Tow and mine slowdowns, and benchmark against a
fully held-out corpus generation. Do not retrospectively relabel
no-risk movement anomalies as definitely transported.
