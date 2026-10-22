# PR #281 — bounded public PQ window auto-selection after real nonconsecutive turns

Date: 2026-10-22. Root cause evidence: [runtime-logs/pq-public-window-g620917-p1-t1/20261022T183106Z_0a3c034f1fac](https://github.com/Numillyash/planets-lab/tree/runtime-logs/runtime-logs/pq-public-window-g620917-p1-t1/20261022T183106Z_0a3c034f1fac).

## Actual observed blocker

The corpus host ran PR #280's evidence wrapper on the frozen approved public game 620917, player slot 1, filenames `player1-turn1.trn` and `player1-turn2.trn`. The GitHub-published sanitized log unambiguously records:

`ABSTAIN_PQ_ARCHIVAL_WINDOW: ValueError: embedded turns are not consecutive`

The runtime metadata says code source `0a3c034f1fac535b1f08b30e1f1a20a711ce24cd` (main), exit 2 and a successful evidence publication. Importantly, **only filename adjacency had been demonstrated**; the two embedded `game.turn` numbers do not have delta exactly +1. Neither the cause (repeat/backward/skip) nor an actual usable transition is known from the old log, so do not invent it or remove the strict check.

## Added bounded selection and diagnostics

`src/planets_lab/corpus/pq_bounded_window_selection.py` loads the **preexisting, immutable** feature-index Parquet and frozen 12-game public allowlist via #278 before touching any ZIP. One caller-explicit allowed `game_id` and player slot defines the only readable perspective; no hidden M2 heldout32 or public100 scan. It lists the ZIP central-directory names without decoding other perspectives, then visits **at most 48 filename-adjacent candidate windows** at/after a caller-specified archive turn (default 1). For each only the TWO selected members are decoded by #279's already bounded reader, which must verify typed game.id, player.id, and embedded delta exactly +1. Only those matching are admitted into a list of at most five privacy-minimal T−1→T field/shape reports. No chosen window is ever inferred from filenames alone.

Invalid windows are separately counted as noncausal `EMBEDDED_TURN_REPEATED`, `EMBEDDED_TURN_BACKWARDS`, `EMBEDDED_TURN_SKIPPED_FORWARD`, distinct identity errors, size-limit errors or generic unsupported. The internal special diagnostic read permits inspecting the *typed embedded-turn difference only* after an explicit strict failure; it **never** promotes a nonconsecutive pair to a valid transition and never emits absolute embedded turns from these invalid pairs. The public report includes only bounded counts, accepted-window slot/turn IDs and aggregated, privacy-minimal per-array/owner freshness facts; no raw .trn, email, username, savekey, messages or private ship/planet details.

Success means **one or more real consecutive embedded-turn candidate windows found**, not successful PQ/PPQ mechanical replay. If none qualify within the bounded scan, write the safe `NO_CONSECUTIVE_EMBEDDED_PAIR_IN_BOUNDED_SCOPE` report and return 2, preserving explicit failure evidence.

## One command for corpus operator

After the PR's exact-head CI success, merge and confirmed post-merge main CI, update on the already configured server once:

```bash
git pull --ff-only origin main
bash tools/run-pq-window-selection-with-evidence.sh
```

The second line is the **entire research run**. Defaults: frozen control12, 620917/player1, filename turn≥1, at most 48 pairs, at most five valid results. Optional already permitted `game-id player-slot first-archive-turn` positional arguments are supported.

The tracked `tools/run-pq-window-selection-gate.sh` runs the existing prebuilt `docker compose run --rm lab` (no `--build`) against existing host archive files. The tracked `tools/run-pq-window-selection-with-evidence.sh` invokes unchanged `tools/run-with-runtime-evidence.sh` with `--include artifacts/pq/selection/game-620917-p1-from1.json`. It automatically publishes the safe summary, complete captured gate stdout/stderr and metadata **even on failure** into the orphan `runtime-logs` branch with run-name prefix `pq-window-selection-g620917-p1-from1`, without switching the source checkout. User need not paste output. Repo write credentials configured on the server are reused; never embed secrets into scripts.

Evidence is `CORPUS_OBSERVED` ONLY for actual archive structural/identity suitability, not independent Host orders/PP/warehouses/RNG/phase/queue parity. `DIFF_VERIFIED` still requires issue #247's accepted orders and full authenticated Host before/after boundary.

## Next

Inspect the newly published `runtime-logs` report through connected GitHub, not by asking the user to send console text. Determine real repeat/skip/backwards rates and actual success-window shape. If no valid pairs at 48, decide on a separately predeclared larger bounded scope or another of six already approved PPQ games; do not weaken strict embedded consecutiveness. Then build and run an aggregate PQ/PPQ source-field sufficiency batch with an equally short evidence launcher. Keep `CURRENT` public68, public100 immutable, sealed M2 heldout32 and unrelated C5/IntelBoard untouched. Each PR must continue to update the ENTIRE `docs/CONTINUE_HERE.md`, PR changelog, substantive docs and verify exact PR/main CI.
