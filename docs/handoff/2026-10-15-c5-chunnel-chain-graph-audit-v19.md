# C5 V19 — targeted time-indexed chain graph and unexplained 25 LY transport

Repository: `Numillyash/planets-lab`, `main`. Keep
production `planets-intel`, combat executor, corpus CURRENT,
external-engine branch, and draft PR #28 untouched.

## Published source evidence

- V17 evidence: `runtime-logs/combat-c5-disjoint-discriminative-chunnel-gates-v17/20261015T121037Z_59dd897f5a79`, pinned published Git blob `a6256b70dc63b9b7126a211245bc65ce20ece863`.
- V18 evidence: `runtime-logs/combat-c5-short-chunnel-and-visibility-audit-v18/20261015T123139Z_a530a2862fff`, exit_code=0, source `a530a2862fff0e61e7bc1131a7b58128ce860271`, pinned Git blob `88bd596534e5e7390c21d6a0a108c732e8a07150`. 20/20 targeted V17 cases reproduced.

V18 discovery:
- G227887/T72: 13 positive candidates from owner 6 to Firecloud 182.
  ALL 13 initiators have neither owner-current nor other fresh
  archive sightings at T; ship 182 has fresh owner **9**, not
  previous owner 6. Original owner 6's perspective IS present.
  Do not attribute to Chunnel failure, destruction or success.
- G338264/T50: Firecloud 234 owner 13 at T−1; fresh T owner **21**,
  and its target 308 fresh owner **29**. A shift of current ownership
  prevents a same-owner endpoint inference.
- G467386/T75: Firecloud 467 (owner 6) at (1141,1459),
  stock target 80 at (1126,1439), distance 25 LY, Warp0,
  fuel 51KT, mission 1, no visible T−1 Tow requests
  against these endpoints. Alongside ship 467 were allied
  ships 193, 235, 405 (owner 6), each Warp 9.
  Fresh owner-current T shows both #467 and #80 at target and
  actor net fuel loss 48 KT. This is unexplained versus
  documented 100LY minimum; avoid claiming actual 25LY Chunnel.

Another important frozen graph relation visible in V17:
G338264/T50 Firecloud #204 at (2971,1728) names nearby
Firecloud #116 at (2971,1727), distance 1 LY, therefore
its own T−1 gate fails the >=100LY requirement. Yet #116
is an independent valid long-distance Chunnel actor to #129
at (2327,1527), and T after Host shows BOTH #204 and #116
at #129's original site with both actor fuel losses 50 KT.
This is a candidate **short first edge plus downstream
long-distance edge**, not proof either edge fired.

## V19 protocol: freeze before T

Pin V17 and V18 byte-identically, verify V17 113/48 census,
V18 original 20-case/14-abstain/6-negative source, and SHA256
of immutable read-only public100 once.

On ALL 48 original V17 T−1 window graphs, identify short
distance-failed edges whose target is also the initiating
Firecloud on an independent, fully gate-passed long edge,
with same owner and exact first-target = second-source T−1
coordinates. Freeze all candidate two-edge graph chains
BEFORE using any posthost T outcomes. Only then compare
historical final owner-current T results from pinned V17.

Separately, before first T owner-current DB read, reconstruct
exact T−1 archived owner-current ship state for **two**
selected windows G338264/T50 (#204/#116/#129/#234/#308)
and G467386/T75 (#467/#80/#193/#235/#405), along with
their existing conservative independent ordinary normal
movement planner endpoints, when available. Planner
abstentions are explicit, not stationary-position proof.

After both windows freeze, compare owner-current T positions
and net fuel differences independently. Do NOT infer game
Chunnel activations from a final-coordinate match. A 25LY
short edge with no downstream edge remains unexplained.
Do not retroactively fit a novel 25LY rule.

This V19 is deliberately POSTHOC on already inspected
V17/V18 episodes, NOT a new held-out accuracy score or
prospective Host execution validation.

## One command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-chunnel-chain-graph-audit-v19-with-evidence.sh
```

Report: `artifacts/combat/c5-chunnel-chain-graph-audit-v19/published/report.json`.
Evidence: `runtime-logs/combat-c5-chunnel-chain-graph-audit-v19/`.

Future: test graph chains on a NEW immutable generation with
outcome-blind selection and explicit intermediate movement
observability where possible. A posthost T endpoint is not
NuHost Chunnel-phase trace; retain ABSTAIN on hidden phases
and game-specific custom mechanics.
