# Combat C2 checkpoint — Classic replay coverage

Date: 2026-09-07

This checkpoint records the completed C2 migration/runtime evidence for the Classic NuHost combat resolver.

GitHub remains source of truth. At the time of this checkpoint:

```text
base main before merge = ce84761ca638d63186080169fd1cc80c39b7d748
C2 branch              = agent/combat-nu-corpus-parity
C2 HEAD                = 99106a72f4dbc0003d3673c733ad9e18692bf232
PR                     = #25
```

## Scope completed in C2

- Added a pure Planets.nu RST weapon/settings adapter for the deterministic Classic resolver.
- Added read-only bulk audit over local cached `validation/corpus/cache/loadall/game-*.zip` archives.
- VCR source is factual `rst.vcrs`; no VCR data is added to the privacy-safe prepared projection.
- Weapon catalogs come from co-observed private RST `beams` / `torpedos`.
- `combatrng` is taken from factual raw RST settings and fails closed when missing/unsupported.
- Duplicate VCR observations are deduplicated by `(game_id, battle_turn, vcr_id)`.
- Payload conflicts and replay-result conflicts fail closed and are reported separately.
- Extended/non-Classic combat RNG remains unsupported.
- Full GitHub pytest is green.

## First 12-game runtime gate

Runtime on all 12 cached loadall archives at pre-fix HEAD `9549094`:

```text
archives                    12
raw_vcr_observations      22256
unique_vcrs                6469
replay_supported           6417
replay_unsupported           52
payload_conflicts             0
replay_result_conflicts       0
partially_supported           0
replay_accounted           6469
malformed_members             0
settings raw_rst members  10450
```

Battle shapes:

```text
ship_vs_planet  3719
ship_vs_ship    2750
```

All 52 unsupported unique VCRs were confined to game `591478`; all had the same reason:

```text
unexpected divide-and-round input
```

No settings manifest was required: factual `combatrng` was present in raw RST for all 10,450 processed turn members.

## Signed arithmetic correction

The remaining 52 cases exposed an error in the first Python port, not a new NuHost mechanic.

Upstream c2ng Host arithmetic uses signed `int32_t` division in `util::divideAndRound()` and `HostAlgorithm::rdivadd()`. C++ integer division truncates toward zero and permits negative numerators. The first Python port incorrectly rejected negative `a` values.

The failing corpus family exercises a negative crew-kill term when `crewdefensepercent > 100`.

C2 HEAD `99106a72` therefore restores C++ signed division/modulo semantics and adds regression tests. No acceptance condition was weakened.

## Final focused runtime gate

After the signed-arithmetic correction, game `591478` was rerun:

```text
archives                    1
raw_vcr_observations     7003
unique_vcrs              2075
replay_supported         2075
replay_unsupported          0
payload_conflicts            0
replay_result_conflicts      0
partially_supported          0
replay_accounted          2075
malformed_members            0
settings raw_rst members  3420
unsupported_reasons          {}
```

Battle shapes for `591478`:

```text
ship_vs_planet  1313
ship_vs_ship     762
```

Because every other supported case in the first 12-game gate completed without entering the formerly rejected signed-arithmetic path, the combined C2 coverage result is:

```text
unique historical VCRs      6469
replay-supported             6469
unsupported                     0
payload conflicts               0
replay-result conflicts         0
malformed members               0
```

## Evidence status

What C2 proves:

```text
CORPUS_OBSERVED + TESTED
```

for complete deterministic Classic replay coverage over the current 12-game historical VCR corpus.

C2 does **not** by itself prove independent factual terminal-state correctness. A VCR supplies its own initial combat state and deterministic seed; replaying it successfully is not an external oracle for the resulting ship state.

Therefore do **not** label the migrated resolver `DIFF_VERIFIED` from C2 alone.

Independent differential evidence begins in C3 using consecutive battles / post-combat factual observations as the external oracle.

## Next phase — C3 explicit ship battle sequences

C3 must proceed from the then-current GitHub `main` after C2 merge.

Required work:

1. extract pure ship battle-sequence carry-over from `planets-intel/backend/app/services/battle_simulator.py`;
2. keep DB/SQLAlchemy/API/UI dependencies out of `planets-lab`;
3. reconstruct consecutive same-turn battles from the raw historical VCR corpus;
4. compare the simulated terminal state of a surviving ship from battle N against its factual starting state in battle N+1;
5. compare at least damage, crew, torpedoes, fighters and shield where semantics permit;
6. preserve explicit Federation/Lizard special-rule evidence boundaries;
7. fail closed on ambiguous chains rather than forcing a match;
8. record per-field match/mismatch counts and every mismatch key.

C3 is the stage that can promote shared combat carry-over behavior to `DIFF_VERIFIED` when independent factual transitions support it.
