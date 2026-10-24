# planets-lab — autonomous next-chat continuation, PR #293

**Source of truth:** https://github.com/Numillyash/planets-lab, live `main`, `docs/CONTINUE_HERE.md` and linked docs. Prepared 2026-10-24 DURING PR #293. Historical verified pre-PR #293 main `70705cb2354759b912b4f3936ce55622e07fc2cc`, final PR #292 CI #1589 and main push #1590 success. This is historical, not a prediction of future live HEAD.

## Context

Продолжай самостоятельно существенную разработку high-fidelity NuHost/Planets.nu simulator `Numillyash/planets-lab` and PlanetDashboard research. **Весь диалог с пользователем веди на русском языке**, включая промежуточные сообщения и итог. Кодовые идентификаторы, имена файлов и ссылки не переводить. Пользователь предпочитает несколько связанных значимых шагов за сессию и один консолидированный результат. GitHub `main` source of truth, не чат. Прочитай live `AGENTS.md`, `docs/WORKFLOW.md`, `docs/ROADMAP.md`, `docs/PR_CHANGELOG.md`, `docs/COMPILED_CORPUS.md` и релевантные `docs/handoff/*.md` перед следующим PR; проверь actual HEAD/CI.

**Обязательный контракт для КАЖДОГО PR:** открой PR до финальных документов, полностью перепиши `docs/CONTINUE_HERE.md` c ФАКТИЧЕСКИМ собственным номером и самодостаточным состоянием/границами; добавь новую запись `docs/PR_CHANGELOG.md` и отдельный substantive roadmap/handoff. Это CI-enforced `tools/check_pr_handoff.py`: не обходить, не ослаблять. Verify exact FINAL head PR CI success → squash merge → actual live main SHA + post-merge push CI success. Не предугадывай SHA/CI.

**Каждый НОВЫЙ on-host/Host/corpus real experiment:** tracked dedicated one-line `bash tools/run-*-with-evidence.sh` using exactly existing `tools/run-with-runtime-evidence.sh`, publishes sanitized JSON+outer log+status+source SHA to separate GitHub branch `runtime-logs` EVEN ABSTAIN. Assistant reads it from GitHub, user не копирует логи. Raw .trn/HAR, private orders/identities/API tokens forbidden in evidence. Synthetic-only CI work needs no fake runner.

## Verified state

- #290 merged: isolated `mine_natural_decay.py` 1–12 turn standard normal/web natural loss `round(units*.95/.85)-1`, Nebula bool, integer sqrt and exact .5 tie ABSTAIN; immutable conditional ledger, **NOT Host phase verified**.
- #291 merged: `minelaying_conversion.py` exact torpedo ammo → `UNALLOCATED` potential mines; 11 standard yields, MD0/MD1..9/MDA/ALL controls and Robot-own-normal fourfold/Crystal web conditional. **No mine placement or Host mission receipt.** Final PR CI #1583/main CI #1584 success, old main `684967df26a220dd3928b469c8a27b747ea11a2b`.
- #292 merged: `minefield_placement_candidate.py` typed full roster source-bounded nearest same-owner same-normal/web center and lowest-ID tie; hypothetical NEW/EXPAND inside integer radius, cap100/150LY and star-cluster exclusion /soft500 ABSTAIN. **No allocated ID, no field mutation.** Verified main `70705cb2354759b912b4f3936ce55622e07fc2cc`, PR CI #1589/main #1590 success.
- #289 frozen public-control12 PPQ 6-game OBSERVATIONAL closure at `CORPUS_OBSERVED`: 48 embedded-consecutive overlapping windows, 22 newly observed owned ship IDs, 17/17 unique prior-base hull+engine matches with 5 ambiguity ABSTAIN, 12/97 persistent control matches, within-window paired 8 no-persistent matches/9 with some; PP unchanged16/increased6/decreased0. NOT 17 Host builds, no causal accepted orders or iid proof; stop posthoc reruns of frozen cohort. `validation/research/pq-public-control12-observational-closure.v1.json`.
- `CURRENT` public68; prepared public100 >26GiB immutable/no rebuild; sealed M2 heldout32 entity rows NEVER open; runtime-logs separate source evidence branch. Host order/warehouses/real accepted orders issue #247 OPEN but **PARKED**, do not request user private HAR or reopen. C5/Horwasp and production IntelBoard untouched.

**CURRENT PR #293:** `feat/minefield-isolated-beam-sweep-ledger-v1`, https://github.com/Numillyash/planets-lab/pull/293. New `src/planets_lab/rules/mine_beam_sweeping.py`, `tests/test_mine_beam_sweeping.py`, [technical handoff](handoff/2026-10-24-standard-isolated-beam-minesweep-v1.md). Official [Minefields](https://help.planets.nu/minefields), [Weapon Technical Details](https://help.planets.nu/weapon-destruction-power), [Minefield Examples](https://help.planets.nu/minefields-examples). Isolated synthetic-only 10 standard beam families normal/web (4/3 through 400/300), full explicit pre-sweep field and ship rosters, exact enemy matrix and ion-storm center map, standard web rate confirmed, ID-ordered ships, each ship affects every eligible in-range field, recalculates radius between ships, strict exact normal <5 LY, web outside-near-edge square ambiguity ABSTAIN, complete typed conservation and conditional field exhaustion. No MSC scoop, fighter/Colonial, starbase sweep, non-Crystal web custom, Host-phase interactions or actual order accepted. **`DOCUMENTED + TESTED conditional` only after exact CI**, not DIFF_VERIFIED. NO corpus/Host run for #293.

**IMMEDIATE NEXT:** inspect PR #293 actual final head and exact PR CI, fix failed CI/test/doc findings without weakening fail-closed, squash merge ONLY green, then verify merged GitHub main HEAD and postmerge push-main CI success. Do not create a new Host experiment or ask operator to copy logs.

## Next actions

1. Finish PR #293 exact CI/merge/main CI and record actual evidence in user final; next conversation always re-query live main status.
2. Next sizable isolated documented mechanic: conservative normal/web mine **MSC scooping** or **Colonial fighter sweeping**, but only with exact source-provenance/range/per-weapon rules and explicit ABSTAIN for any ambiguous rates, integer rounding, ownership, cargo capacity, phase, or starbase/campaign modifiers. Alternatively prioritize authenticated source discovery before code. Do not claim arbitrary combinations form a Host turn.
3. Preserve separate evidence distinction: `DOCUMENTED`, `TESTED`, `CORPUS_OBSERVED`, `DIFF_VERIFIED` are NOT interchangeable. No production IntelBoard, paused C5/Horwasp, parked #247 or frozen PPQ repetitive correlations.
4. For ALL future PRs: full numbered CONTINUE_HERE, numbered changelog, meaningful separate docs; exact PR head CI success and postmerge main CI; user interaction always Russian.

## Boundaries

#290 isolated natural decay ≠ #291 unallocated torpedo conversion ≠ #292 hypothetical spatial candidate ≠ #293 conditional single-phase beam sweeping. Unknown actual accepted orders/turn boundary/field IDs/priority interactions, web near-edge, directed miN, MDH/MDQ, countermining, dense custom, exact .5 tie rounding, MSC, Colonies fighter, campaign starbases, and non-Crystal web modifiers must ABSTAIN. Maintained source/phase privacy rules; no new Host/corpus evidence in #293.
