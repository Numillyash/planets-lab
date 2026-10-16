# C5 bounded freeze and M2 planetary Host active — 2026-10-16

## Engineering decision

**STOP the serial Chunnel/Horwasp residual research loop.** This is an
explicit scope change. It is not a claim that the full NuHost Host queue,
mine/Chunnel phase ordering, capture side assignment, or planet battle
participation has been reverse engineered.

The objective remains an end-to-end useful simulator, but *progress is
measured by independently runnable vertical slices*, not by how many
archival corner cases can be explained retrospectively.

## Immutable C5 research freeze

Last V27 successful runtime:
`runtime-logs/combat-c5-moving-target-visibility-foreign-v27/20261016T165525Z_d4daf2908325`
on clean main `d4daf290832579b7da538c44799c4881e585f0b1`;
`exit_code=0`, 3 published reports, one SHA256 manifest.
No N+1 VCR, no new mechanically promoted Chunnel rule.

Previously validated bounded non-capture ordinary STANDARD
next-pair gate: **22/22** exact transitions in both historical
strict/conditional scopes; this excludes capture predecessors.
Capture continuity has tests and separate bounded differential
gates, but post-capture LEFT/RIGHT O-branch, unresolved arrivals,
and ship→planet ownership/phase interactions remain OPEN.
Existing C5 code under `src/planets_lab/rules/combat/` retains
its fail-closed boundaries, especially
`site_executor.select_temporary_capture_continuation(...,
allow_unvalidated_o_branch=False)`. Do not silently count
ABSTAIN/UNRESOLVED as correct predictions.

V27 game-disjoint archival public8 findings:
58 conventional-long Firecloud actor edges: 55 at frozen target
T, one elsewhere (but observed together with moved target),
two owner-current unavailable. All 56 observed actors end at
the *T observed target*, but this is retrospective endpoint
coincidence, NOT independent Chunnel phase validation.
Both unavailable owners' T perspective member records are
present; T+1 records absent for those cases.
Foreign-owner source appearances 8, at frozen target 7,
in five source episodes of one game. No direct waypoint Warp
or inbound Tow request among those eight T−1 cases;
passenger eligibility and causality UNRESOLVED.

Stop generating single-episode Chunnel V28, V29, etc unless
new authentic Host-phase evidence is supplied or a
well-scoped end-to-end blocker appears. Preserve all artifacts,
runners, provenance, tests and frozen original outcomes.

## C5 support versus unsupported — frozen architecture

Supported bounded:
- Classic pairwise VCR replay; ordinary ship sequence carry-over;
- attributable ordinary no-starbase C4 and starbase shield carry;
- existing non-capture STANDARD queue on scoped validation;
- mutable capture ship identity, membership and temporary
  C-forward selection where independent evidence allows it.

NOT supported as universal/final:
- capture LEFT/RIGHT universal O branch;
- independent Host battlefield arrival completeness;
- short Chunnel stabilizer activation or phase ordering;
- arbitrary special/campaign/Horwasp rules;
- full site mixed ship/planet diplomacy queue;
- starbase hidden damage state;
- any *complete turn* exact NuHost match.

Keep these paths as explicit fail-closed / unavailable and do
not degrade already accepted C2/C3/C4 and C5 primitive tests.
Do not merge draft PR #28 or touch production `planets-intel`.

## Transition: M2 planetary economy / production

The existing repo ALREADY contains
`src/planets_lab/sim/planetary_host_pipeline.py`, a canonical
explicitly incomplete ordered pipeline with 14 implemented
planetary phases, plus mining and factory/tax tests. Do not
reinvent them or claim historical parity.

New tracked `tools/diagnostics/planetary_multiturn_baseline_v1.py`
adds an initial **3-turn internal integration contract** over
two owned planets (distinct races) and one unowned planet,
actual canonical phase classes and deterministic seeds, with
input-state immutability, resource nonnegativity, replay
repeatability and unowned production/tax controls.

This is `TESTED` as an internal simulator fixture only;
there is *ZERO* new historical archive differential evidence.
We do not claim economy is reconstructed end-to-end.

Next M2 implementation after initial baseline:
1. derive source-typed, owner-current, T−1/T planet
   fact pairs using immutable public100/public8 DuckDB;
2. select an independent validation subset by game/turn
   metadata BEFORE comparing outcomes;
3. compare only **attributable** phase families (taxes,
   supplies, mineral extraction, growth), abstaining
   when player actions, production, race-specific changes,
   hidden game options or missing archived perspective
   prevent a unique before/after attribution;
4. keep source facts separate from inferred Host actions;
5. gate any formula or ordering promotion on external
   NuHost-compatible differential validation.

Use one multi-phase wrapper per meaningful checkpoint.
Avoid another month of nested one-case diagnostics.

## One server command for the new M2 internal baseline

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-planetary-multiturn-baseline-v1-with-evidence.sh
```

Output `artifacts/planetary/multiturn-baseline-v1/published/report.json`;
evidence `runtime-logs/planetary-multiturn-baseline-v1/`.

This runner does NOT rewrite the combat resolver, immutable corpus
`CURRENT`, production `planets-intel`, or research external branch.
