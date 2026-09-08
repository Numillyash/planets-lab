# Planets.nu combat C5 — Work transfer entrypoint — 2026-09-08

Use GitHub as the only source of truth. Do not reconstruct current state from chat history. Inspect actual `main` and `agent/combat-c5-host-phase` refs first, then read:

1. `docs/handoff/2026-09-08-combat-c5-host-phase-current.md`
2. `docs/ROADMAP.md`
3. `docs/COMPILED_CORPUS.md`
4. `docs/ARCHITECTURE.md`
5. `docs/WORKFLOW.md`

## Transfer checkpoint

Last CI-verified C5 code HEAD before transfer docs:

```text
8b8f0b43b9d45da4c5b35796e2fa388b6e17fcd9
```

Actual branch HEAD will be later because this transfer/handoff documentation is committed after that code checkpoint. Inspect the ref rather than trusting the recorded SHA blindly.

Current `main` at transfer inspection:

```text
030f7489fd94a2af8e60a7da710c9b28b207f152
```

C5 and current `main` diverge from merge base `89b5b0f1...`; the three main-only commits are movement/fuel-only and have no combat overlap. Synchronize deliberately if useful.

## Closed ordinary C5 evidence

- factual queue: 3,132 ordinary combat sites, 0 ship/planet phase-order violations;
- canonical pre-combat orders snapshot: `T-1`;
- `mission 3 = Kill!`, `mission 7 = Intercept`, `mission 20 = Bird Cloak and Intercept`, `enemy = Primary Enemy`;
- signed exact-three-character FC `[+/-][0-9][0-9]` is `CORPUS_OBSERVED + DIFF_VERIFIED`, not documented;
- isolated ordinary standard left/right: `413/413` exact after C&I reclassification;
- factual isolated C&I attacker: `7/7` right;
- Priority Intercept observed ordinary linked-pair subset: `37/37` pre-standard prefix exact and `37/37` PIA attacker right;
- reverse Ship-ID ordering for multiple PIA attackers remains only `DOCUMENTED` because corpus has no comparable ordinary case;
- game `591478` remains a separate special/campaign/Horwasp bucket and must not tune ordinary mechanics.

## Immediate next gate

The residual-enrichment run on `d608c7d` is complete: 12 archives, 0 payload conflicts, exactly 2 ordinary residuals, 87 separate special-game residuals, and 3 targeted tests passed (user-operated WSL/Docker).

Both ordinary rows have been inspected; their causal explanations remain OPEN:
- `511506/T19/VCR13`: Firecloud80 (027, Kill/PE) left; Meteor89 (2eC, Intercept80, PE=0) right.
- `621896/T28/VCR67`: Gorbie62 (001, Intercept38, PE=2) left; T-Rex38 (eqe, PE=5) right.

Read the current handoff for complete fields, canonical keys and evidence boundaries. Combat rules remain unchanged.

Next run the existing `tools/diagnostics/combat_host_diplomacy_residual_audit.py` for:
- game511506, battle-turn19, player-a6, player-b5;
- game621896, battle-turn28, player-a5, player-b2.

It selects T-1 automatically. Do not repeat the 12-archive enrichment just to rediscover the two rows. Asymmetric diplomacy and leading-integer FC parsing are hypotheses only; neither is a closed rule. Preserve fail-closed behavior and inspect both cases before promotion.

After those two rows:

1. matching Friendly Code exceptions / Harmonic Weapon Modulation boundaries;
2. dynamic multi-ship opponent selection;
3. PIA/C&I pair selection in the dynamic queue;
4. capture/reinsertion and ownership changes;
5. between-phase repair and ship-vs-planet ordering;
6. special game `591478` sequence semantics separately.

## Research rules

- preserve `DOCUMENTED`, `CORPUS_OBSERVED`, `INFERRED`, `TESTED`, `DIFF_VERIFIED` distinctions;
- unknown branches fail closed;
- do not name numeric mission codes without evidence;
- raw `.trn` / loadall data only through narrow privacy-safe diagnostics;
- raw archives/prepared cache/compiled corpus remain local and gitignored;
- do not rebuild L1/L2 unless required;
- after material results update durable handoff/ROADMAP/COMPILED_CORPUS as appropriate;
- use `python3` on the WSL host, or preferably `docker compose run --rm -T lab python ...` for project Python.
