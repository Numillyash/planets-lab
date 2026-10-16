# M2 historical archive differential V1 — T identity fail-closed correction

## Root cause

The first server attempt
`runtime-logs/planetary-historical-differential-v1/20261016T173633Z_9d703d2c9d0a`
completed source T−1 freeze for 32/32 windows and progressed through
postHost archive reads up to G608293/T2 (POST 29/32).
Strict `v9.pre_snapshots(conn,game=608293,before=2)` raised exactly
`ValueError("untrusted Tminus1 archive identity")`. This strict
validator accepts only exact archive game/turn, exact embedded turn,
matching parsed payload game ID/turn and exact perspective identity.
The error is about the T **archive trust boundary**, not about the
economic simulator's prediction. We do not know from the short error
message which individual member or identity field disagrees.

Original evidence meta is clean source main
`9d703d2c9d0a7e7aac8b5afa57f9a40ae6006750`,
`exit_code=2`, missing output directory because the original runner
published only after the entire comparison. No original run's
32-window research outcome was published.

## Surgical change

Keep the strict v9 parser and its full-game/turn/perspective gate
UNCHANGED. In M2 **postHost T only**, wrap the three explicit archive
integrity failures in a fail-closed abstention result:
- exact game/embedded identity mismatch -> `ABSTAIN_T_ARCHIVE_IDENTITY_UNTRUSTED`;
- player perspective mismatch -> `ABSTAIN_T_ARCHIVE_PLAYER_IDENTITY_UNTRUSTED`;
- no exact T archived perspective members -> `ABSTAIN_T_ARCHIVE_MISSING`.

Reject the **entire affected T window**, not an inconsistent subset
of T perspectives. Preserve every already-frozen T−1 prediction,
continue to all remaining metadata-selected windows, and record each
ineligible T window's actual `ABSTAIN` rows under all four families.
Do not include them in conditional exact/mismatch denominators. New
summary keys: `T_archive_context_rejected_windows`,
`T_archive_context_rejection_rows`, and existing `status_counts`.
Rerun the SAME 8 games, SAME 32 deterministic metadata windows,
SAME generation and SHA256, and same M2 model. All unexpected
ValueErrors, database errors or model exceptions continue to abort.

No C5 code or NuHost formula changes. No relaxation of corpus identity
checks. No N+1 VCR, no CURRENT switch, no earlier false positive
claims. Existing CI tests plus new regressions verify that one invalid
T2 window cannot invalidate remaining windows or count as mismatch,
the global PRE barrier holds, and unrelated exceptions still raise.

## One command, after PR and main CI pass

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-planetary-historical-differential-v1-with-evidence.sh
```

Successful evidence publishes four original families and manifest to
`runtime-logs/planetary-historical-differential-v1/<runid>`.

## Next acceptance criterion

Read all four published reports and archive-abstention coverage before
adjusting *any* economy formula. Conditional full-stock deltas contain
unmodelled player-order and transfer effects: don't recast any mismatch
as proof of a defective mining, tax, supply or population formula.
