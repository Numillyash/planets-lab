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

Historical `main` at initial transfer inspection:

```text
030f7489fd94a2af8e60a7da710c9b28b207f152
```

That initial three-commit divergence is historical. At the return-from-Work inspection, main was `b3cc67dcee669ce84b8ff14a3237a0e69ab10707` and C5 was `5be8993c57aa0eddc811e13c8231fe724af89612` before this documentation update. Inspect actual refs and delta; no branch synchronization was performed.

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

The directed diplomacy gate is also COMPLETE. Both exact pairs have symmetric `(relationto, relationfrom, conflictlevel)=(1,1,0)` in each direction, with matching owner perspectives and `mirror_consistent=true`. The asymmetric T-1 diplomacy hypothesis is rejected for both cases. Complete numeric evidence and local artifact paths are in the current handoff.

**Resume in the project chat.** The user ended Work execution because of its limits. Next prepare one narrow source-context audit for the same two cases: owner-visible `T-2/T-1/T` records with freshness/provenance, selected mechanical VCR fields, and all same-turn appearances of the two ships to inspect state alignment and possible queue/capture context.

That new diagnostic has **not been written or run**. Do not invent a ready script name. Do not repeat the completed 12-archive enrichment or the two diplomacy runs. Leading-integer FC parsing (`2eC -> 2`) remains an unverified hypothesis and cannot explain the separate Gorbie/T-Rex case. Rules are unchanged; unknown branches fail closed; no new mechanic was promoted to `DIFF_VERIFIED`.

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
