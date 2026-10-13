# Research direction checkpoint — park Horwasp, resume ordinary C5 queue

Date: 2026-10-14. Canonical repository: `Numillyash/planets-lab`, branch `main`.
This is a **prioritization and evidence-boundary decision**, not a new
mechanical prediction and not a change to the production combat executor.

## Decision

**Pause new Horwasp-specific research** (mass interpolation beyond the frozen
hypothesis, terminal clan loss, fighter-feedback game-generation gate, fighter
regeneration, VCR-ID phase ordering, special Horwasp queue branches). Do not
delete any code, tests, data, handoffs or evidence, and do not reinterpret
existing failures as successes.

Reason: five observed same-turn Horwasp transitions have already received
multiple increasingly narrow experiments while the full Host combat phase,
engagement ordering, capture continuation, site state and general mechanics
have substantially broader reach. More Horwasp residual work currently has
poor marginal value relative to finishing ordinary NuHost C5 coverage.

Treat race 12 / special Horwasp cases as **explicit unsupported / out-of-scope**
for ordinary acceptance; never silently count them as successes. Existing
historical controls may be retained for preventing regressions.

## Final frozen state (no new run required)

Published last successful runtime evidence:

`runtime-logs/combat-horwasp-fighter-feedback-gate-v1/20261013T233438Z_2e1a959931cd`

Source commit: `2e1a959931cdf371cc12a41a96052a8e352907a9`.
Published report Git blob SHA-1:
`5ca53b4fc3fb3f9c1e0e3b8d5a43404750135276`.

Five repeated Horwasp transitions, three game/turn windows:

- Exact conditional next-mass equality: feedback OFF 2/5, ON 1/5.
- Exact conditional next-fighter equality: feedback OFF 1/4, ON 0/4.
- Game creation-date gate: `ABSTAIN_GAME_CREATED_DATE_NOT_AUTHENTICATED`
  on 5/5; do not choose a branch by numerical fit.
- Three G350094/T153 transitions still miss even with feedback OFF:
  +33 KT, +43 KT, +84 KT (factual minus candidate).
- No terminal Host clan reconstruction, no independently proven VCR-ID
  execution chronology, no generative full combat-mass prediction.

The earlier broad independent non-Horwasp/ Horwasp-containing mass stress
contained 24 new independent games / 424 sides; 353 conditional hull+race
component equals factual mass, 71 observational residual sides.
Do not overclaim 353/424 as complete Host-predictor accuracy or expand
mass-exploration just to erase every anomaly.

Useful retained evidence:

- `runtime-logs/combat-mass-independent-late-turn-stress-v1/20261010T225044Z_95ed2f51e7bb`
- `runtime-logs/combat-mass-late-residual-prestate-audit-v1/20261011T141334Z_45a3eaf8d143`
- `runtime-logs/combat-mass-horwasp-tminus1-first-vcr-v1/20261011T175403Z_db2d9a037bdb`
- `runtime-logs/combat-horwasp-terminal-continuity-v1/20261011T194131Z_e3ac3071609d`
- `runtime-logs/combat-horwasp-postcombat-clan-projection-v1/20261011T200111Z_e6a4787a2300`

## Restart ordinary Host C5 (higher impact)

Read `docs/ROADMAP.md` and
`docs/handoff/2026-09-22-combat-predictive-queue-runtime.md`.

The bounded ordinary selector-backed historical gate with the existing
`combat-planar-no-horwasp` scope already has **22/22** held-out next-VCR
transition exact comparisons, both strict and conditional. It excludes
capture predecessors from its exact-set subset; this is **not** a proof
of capture continuation.

The `400330/T141` mutable site replay integration also already passed
**3/3** in
`docs/handoff/2026-10-07-site-combat-terminal-replay-v1.md` using
current-VCR-N replay with N+1 held out. This is bounded, not free-running.

Recommended next implementation order:

1. **Main workstream:** improve independent multi-site / multi-game
   ordinary non-Horwasp C5 queue selection, prioritizing capture state,
   parent-queue resumption and ship/planet transition across changing
   owners. Reuse existing code in `src/planets_lab/rules/combat/`
   and `tools/diagnostics/combat_host_*.py`; avoid another niche
   mass-residual deep dive.
2. Revalidate the existing `combat-planar-no-horwasp` strict population
   without leaking future VCR N+1 (or next capture side) into prediction.
   Add explicit no-op/abstention categories for unsupported targetabilities,
   special rules, missing T-1 perspective and unproven O branch.
3. Expand genuinely independent ordinary held-out games/sites rather than
   tuning the already-open capture-side corpus. Capture-side candidate
   fitted the 102/102 open population after a **failed prospective gate**:
   see `docs/handoff/2026-10-05-public100-capture-side-prospective-result.md`.
   Keep it research-only until fresh branch-balanced evidence supports it.
4. Later, broaden core Host coverage to movement/planet production, mines,
   general missions, diplomacy and visibility; return to Horwasp only when
   necessary for a concrete end-to-end integration blocker or a separately
   funded special-race milestone.

Tracked existing gate (only if needed for broad C5 baseline):

```bash
bash tools/run-combat-capture-reintegration-with-evidence.sh
```

This is *not* a request to rerun any Horwasp-specific experiments.
Before issuing a new server command, inspect current `main`, the latest
runtime evidence and whether existing acceptance already covers the
chosen ordinary path. Keep server evidence wrappers and read-only
corpus access.

## GitHub and merge boundary

GitHub `main` is the only code source of truth. Keep
`research/external-engine-analysis` separate.

The old C5 queue work-in-progress **PR #28**
(`Audit factual Host combat queue shapes`) explicitly requests
**remain draft/open, never merge or mark ready without explicit
instruction**. Preserve this restriction; use new `main`-based
feature branches/PRs for further canonical development.

No `planets-intel` production change. No unverified Horwasp, Shield
Generator, RNG or capture-side formulas promoted into the main executor.

## Conditions to reopen Horwasp

Reopen only with a reproducible ordinary-pipeline blocker, an independent
Host phase/creation-date observation that discriminates previously
unresolved hypotheses, or an explicit reprioritization request. Do not
reopen simply because residuals remain nonzero.
