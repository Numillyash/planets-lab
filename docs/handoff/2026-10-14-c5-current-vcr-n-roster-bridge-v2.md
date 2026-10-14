# C5 ordinary current-N roster bridge V2 (conditional, research-only)

Date: 2026-10-14. **Horwasp remains paused**. Source of truth `main`.

## Frozen independent evidence and failure analysis

Full published parent-forward V1 evidence:
`runtime-logs/combat-c5-ordinary-parent-forward-v1/20261014T043205Z_f15a725d4cfe`.
Immutable Git blob SHA1 `1ed69919f38fbc7d09b2e890162c1a25a3f677bd`.

Original V1 source sites:
`runtime-logs/combat-c5-public100-site-coverage-v1/20261014T041550Z_fb5c5dfcc89e`,
Git blob SHA1 `fda92475988d2f7dfbc7b93606de4f8cec909806`.

Fixed population: 48 game metadata-preselected games, 96 windows,
27 ordinary ship-only multi-VCR sites, 63 adjacent VCR-ID transitions.
Current data is **already open exploratory data**, not a fresh holdout.

Strict ordinary C5 V1 summary: 56 transitions attempted,
7 unavailable from site context; 47 current replay/start abstentions,
3 parent STANDARD resolved choices (2 exact, 1 mismatch),
2 capture-path abstentions, 4 non-selection parent-path abstentions.

The detailed 47 current replay/start reasons are:
**40 current N participants absent from strict T−1 predicted active site state**
and 7 current-N-start/carried-state mismatches. The latter are NOT silently
corrected. Four site contexts altogether account for 7 missed transitions.

The observed wrong parent selection example:
G245693 T103 V1024 -> V1025, prediction pair [449,539],
factual [449,519]. Keep this mismatch intact.

## V2 question and exact safety boundary

We have two different research claims that must NEVER be mixed:

1. **Strict independent T−1**: predict site physical membership, state,
   queue and N+1 without observing incoming ship N at all. This remains
   V1's frozen 3/63 computed next pairs and 2/3 exact.
2. **Current-N-conditioned queue only**: condition on physical presence,
   owner and mutable state of the two already observed ships in VCR N,
   then independently compute the N terminal and next N+1 parent-queue
   selection. This does NOT verify precombat site membership or full Host
   autonomous prediction. An exact conditional pair must not be reported
   as a strict site or Host result.

The V2 source diagnostic
`tools/diagnostics/combat_c5_current_n_roster_bridge_v2.py`
preserves BOTH original published source reports via bytewise Git blob
verification and the immutable SHA256-pinned public100 DB, opened
read-only. The exact 27-site/63-transition denominator is invariant.

For each selected transition:

- Build site T−1 predicted roster, order and diplomacy independently,
  reuse factual site history with IDs STRICTLY less than N.
- If a current-N VCR participant is missing from active site roster,
  only anchor it if (i) a corresponding **independent T−1 owner ship**
  exists; (ii) same owner, hull and race; (iii) that ship has NOT
  already appeared in an earlier same-site VCR; (iv) the current N
  participant has a full valid physical combat start vector. The
  position of N is explicitly supplied by observed N, not claimed
  as predicted movement. Record original T−1 predicted position.
- **Never overwrite a carried ship** whose current start disagrees
  with the VCR; those seven mismatches remain ABSTAIN. Do not
  resurrect a previously fought destroyed ship.
- Replay N using factual N setup/seed, apply terminal and, for
  NONCAPTURE cases, build T−1 order/through-N diplomacy parent
  STANDARD inputs, call `select_parent_resume`.
- Capture is still an explicit ABSTAIN: no game-specific fixture,
  no next opponent supplied by N+1.
- Only then compare predicted pair and L/R with factual N+1.
  Store both V1 strict status and V2 conditional status per
  frozen transition. Never silently convert a conditional match
  into an independent game-state prediction.

V2's purpose is to **separate the movement/site-roster bottleneck from
the selection algorithm bottleneck**. An observed larger conditional
denominator does not advance the full end-to-end NuHost accuracy,
but tells us where to invest next (site membership/movement or Host
pair selection). A low denominator or new mismatches must be
reported unchanged, not explained away by retuning.

## Implementation and validation

- `tools/diagnostics/combat_c5_current_n_roster_bridge_v2.py`
- `tests/test_combat_c5_current_n_roster_bridge_v2.py`
- `tools/run-combat-c5-current-n-roster-bridge-v2.sh`
- `tools/run-combat-c5-current-n-roster-bridge-v2-with-evidence.sh`

Tests cover valid independent T−1 identity gate, missing/owner
conflict, no previously-fought ship resurrection, no correction
of carried state, no N+1 oracle and fail-closed capture handling.

## One server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-current-n-roster-bridge-v2-with-evidence.sh
```

Output:
`artifacts/combat/c5-current-n-roster-bridge-v2/published/report.json`
and published evidence under
`runtime-logs/combat-c5-current-n-roster-bridge-v2/`.

No changes to `planets-intel`, production or canonical combat
executor. No `CURRENT` mutation. Preserve draft PR #28 open.
