# Horwasp VCR-ID terminal continuity / causal holdout audit V1

Mainline research continuation after PR #169, successful source runtime:
runtime-logs/combat-mass-horwasp-tminus1-first-vcr-v1/20261011T175403Z_db2d9a037bdb.

Source Git blob SHA-1: 358c354d424907488dffd3665e6d6d07c8d04f64.
Source reports 26 Horwasp sides (21 first-by-ID, five repeated-by-ID),
four repeated ship chains (five adjacent-in-chain transitions).
Twenty initial sides match the independent T-1 clan floor hypothesis;
the remaining initial side is +360 KT with an observed fighter-bay
opponent. Four of five repeated observations diverge −4/−34/−57/−225
KT, one matches. The earlier mass audit already pinned all T-1 clans.

## Independent terminal continuity question

Does the deterministic, already implemented NuHost Classic current-VCR
replay of encounter N generate terminal damage, crew, shields,
ammunition and fighters consistent with the same ship's later factual
start vector at N+1 when sorted by VCR ID?

Unlike interpolating clans from a later observed VCR mass, replay can
compute these five terminal fields without opening any N+1 state.
Replay does use current VCR N's factual participants, seed, combat
configuration, weapon catalog and Classic RNG. Therefore this is a
constrained, current-VCR-based phase continuity test, not a free-running
Host, independent battle-pair prediction or proof of VCR-ID chronology.
The Classic replay does not produce terminal Horwasp clans.

## Selection, controls and fail-closed protocol

1. Pin exact published 26-side Horwasp report using Git blob identity.
2. Open immutable public100 DuckDB using explicit SHA256, read-only,
   never CURRENT, never production databases.
3. Derive the exact four frozen repeated Horwasp ship identities,
   game turns and VCR IDs. Verify all frozen side masses and owner/race
   identity against source current VCRs; no hidden remapping.
4. In the same three game-turns, include all other repeated
   ordinary-ship owner/identity chains as metadata-selected controls.
   Select without inspecting mass, replay terminal or success rates.
   Keep the controls separate even if there are none.
5. For each adjacent-by-ID appearance of a ship, load the first VCR
   N, run its deterministic Classic replay and record terminal fields
   or explicit ABSTAIN_CLASSIC_REPLAY_UNAVAILABLE if unsupported.
   Then (after replay) compare replay terminal values with factual
   next VCR start at N+1: shield, damage, crew, torpedoes, fighters.
   Do not use N+1 mass or current N+1 RNG to generate N terminal.
6. A replay-declared destroyed/captured ship reappearing is labeled
   explicitly rather than explained away by a hypothetical capture.
   Field mismatches and incomplete replay fields fail closed.
7. Preserve game/turn/ship/side/VCR identities, chain status and
   current-only observed mass delta. Never backsolve Horwasp clans
   or add unseen mechanisms to force agreement.

All five original Horwasp chain transitions must be accounted for.
For every matched carry result, evidence supports one possible
ID-order hypothesis in that studied chain only. Without independent
host scheduling evidence, no report declares VCR-ID order as proven.
A mismatch can reflect unsupported/non-Classic combat, setup/seed,
phase effects, or incorrect ordering; it does not alone prove an engine
rule. Controls are observational, not independently randomized samples.

## Running on server

    cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-combat-horwasp-terminal-continuity-v1-with-evidence.sh

Local:
artifacts/combat/horwasp-terminal-continuity-v1/published/report.json

Evidence branch:
runtime-logs/combat-horwasp-terminal-continuity-v1/

CI validates semantics, source integrity, abstentions, terminal
comparators, and negative cases. Actual Classic replay support
and transition counts must be confirmed from server runtime.
Do not change planets-intel, mass executor, corpus CURRENT or
promote Horwasp attrition as reconstructed.
