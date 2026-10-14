# C5 ordinary combat: T−1 spatial-site error attribution V3

**2026-10-14. Research only.** Mainline repository: `Numillyash/planets-lab`.
Horwasp remains explicitly out of scope.

## Inputs: immutable server evidence

- Metadata-preselected public100 census:
  `runtime-logs/combat-c5-public100-site-coverage-v1/20261014T041550Z_fb5c5dfcc89e`
  — published report Git blob:
  `fda92475988d2f7dfbc7b93606de4f8cec909806`.
- Conditional current-N roster V2:
  `runtime-logs/combat-c5-current-n-roster-bridge-v2/20261014T044822Z_9ace8839a471`
  — published report Git blob:
  `dd641864dc3bd541098ea2c21cf21fb8ff03d5ce`.

V2 verified: 27 ordinary ship-only multi-VCR sites, 63 adjacent ID
transitions, 56 attempted and 7 without reconstructed site context.
There are 9 **current-VCR-N-conditioned** next-pair predictions:
7 exact, 2 mismatched. The stronger fully strict T−1 precursor
remains 3/63 predictions, 2 exact.

The largest blocking status is 25
`ABSTAIN_PARENT_STANDARD_NO_PAIR`; eight more are
`ABSTAIN_PARENT_STANDARD_UNRESOLVED`. The V2 roster bridge revealed
that observing only the ships in current VCR N can still omit
**other** ships physically arriving at the same battle site.

## Question: site membership vs selector logic

For every frozen transition, analyze the *independently precomputed*
T−1 movement/site prediction of the two **factual future** N+1
participants, **after** the published V2 status and predicted
pair have been fixed. Do not feed factual N+1 ship IDs, owners,
coordinates or selection outcomes into any forward selector.

For each observed next-ship identity, report:

1. Whether independent T−1 owner-ship and predicted final position exist.
2. Whether T−1 forecast position equals the site's known coordinates,
   points elsewhere, or is unresolved.
3. The original T−1 movement-source code (e.g. special movement,
   mine risk, Tow, Chunnel, ordinary movement) as data, WITHOUT
   interpreting unknown source codes as proven mechanics.
4. Whether the ship appeared in VCR N or any earlier factual
   same-site battle (observation only).
5. Whether a different owner is observed at N+1 than T−1,
   which may indicate intervening capture and must not be silently
   treated as normal movement.

Cross-tab these classes separately for 25 NO_PAIR, 8 UNRESOLVED,
8 replay-start mismatches, 5 capture-order abstentions, nine
conditional predictions and 7 site-context failures. Show which
class dominates before prioritizing a concrete *general* movement
or state-carry implementation.

## Strict scientific boundaries

- This V3 makes **zero new next-VCR queue predictions**.
- It does **not** improve the already frozen V2 score, alter selectors,
  backsolve missing ship positions, or substitute future N+1 opponents
  into parent queue candidates.
- The V3 investigation is retrospective failure attribution on
  already-open cases, **not an independent validation cohort**.
- Case identities, statuses and denominators all remain frozen;
  game-turn/site preselection remains the original 48/96 metadata
  selection.
- Pinned public100 DuckDB is read-only; SHA256 verified once:
  `3c9604f0691e3fa0d13c1c7d789a855f390f4c9e1df0d8ff97900cedbd064f0c`.
- The original V1 incorrect G245693 T103 449–539 vs
  factual 449–519 remains a genuine mismatch. No tuning here.

## Implementation

- `tools/diagnostics/combat_c5_tminus1_site_recall_attribution_v3.py`
- `tests/test_combat_c5_tminus1_site_recall_attribution_v3.py`
- `tools/run-combat-c5-tminus1-site-recall-attribution-v3.sh`
- `tools/run-combat-c5-tminus1-site-recall-attribution-v3-with-evidence.sh`

### Server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-c5-tminus1-site-recall-attribution-v3-with-evidence.sh
```

Evidence branch:
`runtime-logs/combat-c5-tminus1-site-recall-attribution-v3/`

The next *implementation* after observing this distribution should
address the largest **independently supportable** site-arrival failure,
not guess opponents from the already visible next VCR. If both
N+1 ships were already correctly predicted at the site but selector
produced NO_PAIR, investigate Standard eligibility, pair occurrence
or phase ordering instead of movement. Horwasp remains paused;
draft PR #28 must remain open and unmerged.
