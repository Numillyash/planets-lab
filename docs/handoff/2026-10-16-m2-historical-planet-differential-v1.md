# M2 historical T−1/T planetary economy differential, v1

## Motivation and prerequisite

M2 internal three-turn baseline passed on clean main
`1129ca77691cd8ae9d0ac5ba1ba4385824378632`:
`runtime-logs/planetary-multiturn-baseline-v1/20261016T172150Z_1129ca77691c`.
Runtime evidence: exit 0, no missing artifacts, 3 simulated turns, 3
planets, source immutable, deterministic, ZERO actual NuHost archive
comparisons. Published report Git blob
`61daf8a929380151d0d1dbf9bccd2d6f5b4a95ec`.
This is the first real archival M2 comparison protocol, NOT a
restart of C5/Chunnel research.

Immutable new public8 historical games, freshly collected for
previous V25 combat work and now prechosen based ONLY on game/archive
metadata (not planet result inspection):
`/root/projects/planets-corpus-db/generations/corpus-v2compact-c5-v25-public8-20261016.duckdb`;
SHA256:
`af4c1579b97736c158cf50a7f709e39b749860661ed65c028fb8085e756c573a`.
Pinned previously published V25 corpus manifest Git blob
`2c89d5320b31b2f12d9235192a8ac31240549052`.
All eight games verified by exact source_archives membership.
Same V25 historic archive corpus; new **M2 test dimensions** but NOT
a prospectively designed independently collected economy corpus.

## ONE batch of four economy measures

- `supplies.json`: predicted final supply stocks from the existing
  ordered planetary pipeline vs observed postHost owner-current T
  supplies, as conditional net-stock comparison.
- `taxes.json`: predicted final MC stocks vs postHost MC. Tax
  source may change from in-game spending, transfers, pillage and
  other unmodeled mechanics: NEVER claim the observed difference
  equals taxation alone.
- `minerals.json`: predicted four surface + ground mineral stocks
  vs archived eight mineral counts; includes existing mining
  and trans-uranium phases, but other transfers/production can
  change the same fields.
- `populations.json`: predicted colonist and native clans vs
  archived T owner-current. Transfers, clans dropped, combat,
  and unmodeled races may affect T totals.

Strict input barrier: pick the SAME 8 new historical games and
four quantile adjacent T−1/T windows per game from compact
`source_members` metadata BEFORE opening any planet state.
Read all 32 windows T−1 only, per window select up to 24
planet IDs with unique owner-current source, owner/perspective
match, fresh `infoturn`, authenticated race. Freeze full
canonical `PlanetaryHostPipeline` conditional forecast per
planet, explicitly labeling unsupported/missing input.
Only after ALL T−1 freeze open T, require current source-owner
perspective and no owner changes. Compare only explicitly
present source/target economic fields; otherwise ABSTAIN.
Report per-game-turn clusters, exact, mismatch and abstentions
separately, with no denominator hiding. Original raw owner
records and personal or account information are NOT persisted.

**Scientific limitation:** T postHost state is NOT a unique
Host-phase economy trace. Even observed exact full-stock matches
do not validate every formula/phase. The model does not incorporate
all player orders, building, Cargo transfers, starbases,
campaign/special abilities, or the full Host timeline.
All matches are `CONDITIONAL_EXACT_ALL_FIELDS` and misses
`CONDITIONAL_MISMATCH_UNATTRIBUTED`; missing data/unknown
races `ABSTAIN_*`. Do not fit unknown modifiers to T output.
No new production behavior promoted in this batch.

Four reports + SHA256 manifest published under
`artifacts/planetary/historical-differential-v1/published/`.
One SHA256 check, read-only opening of exact public8 generation,
no CURRENT interaction, one single runtime evidence wrapper.
No C5 source changes, no Chunnel research, PR #28 kept Draft.

## Exact one-line server command

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-planetary-historical-differential-v1-with-evidence.sh
```

Future: based on this FIRST real result, prioritize a supported
economy comparator slice with evidence of absent interfering
operations and complete phase order; stop after one bounded
attribution batch instead of indefinite single-residual chases.
