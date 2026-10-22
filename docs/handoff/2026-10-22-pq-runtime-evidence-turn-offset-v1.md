# PR #280 — PQ archival-turn identity and one-command GitHub evidence

Date: 2026-10-22. Real input: the existing approved public-control12 PQ candidate **game 620917, player slot 1, filename/archive turn 1→2**. On the operator's corpus Docker host, PR #279 initially returned `ABSTAIN_PQ_ARCHIVAL_WINDOW: ValueError: embedded game/turn/player identity mismatch`. No raw archive payload, private key or orders were transferred to the repository or conversation.

## Root issue

The old PQ probe incorrectly asserted `game.turn == filename/archive turn` for each `.trn`. The mature `src/planets_lab/corpus/normalizer.py` already stores **both** `ArchiveTurnSnapshot.archive_turn` and `embedded_turn`; it checks game ID and player ID and separately reports whether adjacent archive members have consecutive embedded turns. These numbering domains must not be conflated.

PR #280 requires each selected member's typed embedded game ID and player ID to match the explicit approved request; it independently requires **two consecutive typed embedded turns**. A nonzero stable archive→embedded offset is allowed and reported, without guessing a fixed +1 convention. Crucially, `infoturn` freshness uses the **embedded** turn rather than the archive filename index. Invalid embedded player/game IDs, typed bool-as-int, nonconsecutive embedded turns and mismatched archives still `ABSTAIN`. This is a guarded inference from the established normalizer, **not a claim the live 620917 archive was already successfully rerun**. Unit tests include offsets -1/+1/+4 and adversarial identity mutations.

New only-public diagnostic JSON fields: `before_embedded_turn`, `after_embedded_turn`, `archive_to_embedded_turn_offset`, `turn_identity_relation` (`EXACT` or `CONSISTENT_OFFSET`). No private entity fields, email, account keys, message text or raw orders emitted.

## New permanent host command

For the default approved single window, use from the source checkout on the corpus host:

```bash
git pull --ff-only origin main
bash tools/run-pq-public-window-with-evidence.sh
```

Further approved windows can be requested with three positional arguments, for example:

```bash
bash tools/run-pq-public-window-with-evidence.sh 620917 1 1
```

The launcher uses `tools/run-pq-public-window-gate.sh` to execute the existing Docker `lab` image without `--build`, with the pre-frozen `pq-public-control12-frozen-cohort.v1.json` and the existing local Parquet feature index. The only selected compressed source member pair stays on the host. The resulting privacy-minimal report is stored under `artifacts/pq/windows/game-<id>-p<slot>-t<turn>.json`, which is gitignored.

**Automatic evidence upload:** the launcher delegates to the existing `tools/run-with-runtime-evidence.sh` wrapper (do NOT reinvent git checkout, push, credentials, or call `git push` from within the source branch). It publishes one immutable log, sanitized report (when successful), provenance metadata and exit code under:

```text
https://github.com/Numillyash/planets-lab/tree/runtime-logs/runtime-logs/pq-public-window-g620917-p1-t1/
```

Each actual run is stored in a further timestamp/source-SHA subdirectory. The wrapper **also publishes failed attempt logs**, and exits with the real failure code or 70 if evidence push fails after a successful gate. Requires configured `origin` write permission on the corpus host; there is no service token stored in scripts or logs. Source `main` remains untouched and no raw archive, env dump, API key or command arguments are published. Never paste private `.trn`, passwords, or HAR to chat. If publication fails, the wrapper prints the local evidence directory; repair SSH/remote push permissions and rerun rather than sending raw logs manually.

## Separate verification milestones

1. The CI checks **synthetic archive formats** and shell syntax, which proves only the stated parser/runner contract at `TESTED` level.
2. After PR #280 exact-head CI/merge/postmerge success, the operator invokes the single command above. The assistant then reads the new `runtime-logs` run by GitHub; no user copy/paste is needed.
3. Read the actual operator-produced report and distinguish genuine `CORPUS_OBSERVED` owner-current row availability from missing/stale/unknown fields; do not infer complete PP/base warehouses, real queued intentions or Host execution from a shape-only report.
4. If the real window still abstains (e.g. game/player identity differs), add a **privacy-safe structured mismatch classifier** first and publish it with the same runner; do not loosen identity checking or echo embedded private payloads.

General rule for future server/corpus gates: create a tracked `tools/run-<gate>-with-evidence.sh` convenience launcher using the existing `tools/run-with-runtime-evidence.sh`, so the user can execute **one short `bash` command and all sanitized results arrive in `runtime-logs` automatically**. No manual transfer to chat.

Issue #247 remains the blocker for independently authenticated NuHost accepted orders, true Host phase placement and full owner before/after state. `CURRENT` remains public68; public100 is not rebuilt, frozen M2 heldout32 entities remain sealed, unrelated C5/combat and IntelBoard production unchanged. Subsequent PRs must meet per-PR handoff/changelog/topic-doc contract #262.
