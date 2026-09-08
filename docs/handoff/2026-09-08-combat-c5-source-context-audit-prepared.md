# C5 Host combat residual source-context audit — prepared gate — 2026-09-08

GitHub is the source of truth. This file records the code-preparation checkpoint for the next C5 historical runtime gate. It does **not** contain historical runtime results.

## Repository state at preparation

Fresh GitHub inspection before this change:

```text
main: b3cc67dcee669ce84b8ff14a3237a0e69ab10707
C5:   e6cbe5c837e0775ee9da92b802756ca3b1d88a56
merge base: 89b5b0f1c06869a0d03d04cba76caa78bc4b10ce
compare C5 vs main: ahead 54 / behind 10
PR #28: open, draft=true
```

No merge/rebase/synchronization with `main` was performed. PR #28 remains draft.

## Closed evidence carried forward

The two ordinary non-PIA `mission=7` standard-side residuals remain:

```text
511506 / battle T19 / VCR13 / ships 80,89
621896 / battle T28 / VCR67 / ships 62,38
```

The completed T-1 diplomacy audit found symmetric directed relation triples `(1,1,0)` for both owner pairs. The asymmetric-diplomacy hypothesis therefore remains rejected for these two rows.

No combat rule, Friendly Code parser behavior, PIA eligibility rule, or evidence status was changed.

## New diagnostic

Prepared:

```text
tools/diagnostics/combat_host_residual_source_context_audit.py
tests/test_combat_host_residual_source_context_audit.py
```

The filename was checked on the C5 branch before creation; no pre-existing tool with this name existed.

The audit is intentionally narrow and privacy-safe:

1. defaults to exactly the two residual cases above;
2. reads owner-visible ship records for `T-2`, `T-1`, and `T`;
3. preserves archive turn, embedded turn, `infoturn`, current/stale freshness and perspective player provenance separately;
4. projects only an explicit ship-mechanics allowlist:
   - owner/hull/position;
   - mission/targets/Primary Enemy/Friendly Code;
   - cloak/warp/waypoint;
   - fuel/damage/supplies;
   - beam/torpedo/bay/ammunition/crew fields when present;
5. non-owner perspectives contribute provenance/freshness plus allowlisted current-value conflict checks, not arbitrary raw payload;
6. deduplicates factual VCRs by ID+payload digest across archive perspectives and reports payload conflicts rather than hiding them;
7. projects only combat-mechanical VCR fields;
8. enumerates **all** same-battle-turn VCR appearances of both tracked ship IDs, including different coordinates and appearances before/after the target VCR;
9. computes only known-overlap T-2→T-1 and T-1→T owner-visible field diffs; missing fields remain unknown;
10. does not infer a Host rule from any observed difference.

The diagnostic intentionally does **not**:
- rerun the 12-archive residual-enrichment audit;
- rerun diplomacy;
- inspect or tune game `591478`;
- modify `src/planets_lab/rules/combat/order.py`;
- reinterpret `2eC` as a leading integer;
- broaden Priority Intercept eligibility;
- label source-state differences as phase-current mutations without evidence.

## Historical runtime gate

Run on the user's WSL repository/archive cache:

```bash
cd /root/projects/planets-lab
git fetch origin
git checkout agent/combat-c5-host-phase
git pull --ff-only origin agent/combat-c5-host-phase

OUT="artifacts/combat-c5-source-context-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

git rev-parse HEAD | tee "$OUT/source.txt"

docker compose run --rm -T lab \
  pytest -q tests/test_combat_host_residual_source_context_audit.py \
  2>&1 | tee "$OUT/tests.log"
TEST_RC=${PIPESTATUS[0]}

docker compose run --rm -T lab \
  python tools/diagnostics/combat_host_residual_source_context_audit.py \
    --archive-dir validation/corpus/cache/loadall \
    --prepared-dir validation/corpus/cache/prepared-v1 \
    --output "$OUT/report.json" \
  2>&1 | tee "$OUT/audit.log"
AUDIT_RC=${PIPESTATUS[0]}

printf 'tests rc=%s; audit rc=%s\n' "$TEST_RC" "$AUDIT_RC"
printf 'artifact dir: %s\n' "$OUT"

test "$TEST_RC" -eq 0
test "$AUDIT_RC" -eq 0
```

Do not commit the generated artifact directory.

## Interpretation gate after runtime

For each tracked ship, classify the evidence without forcing a rule:

- **source-state alignment issue** — owner/current provenance or identity/freshness disagrees in a way that invalidates the assumed T-1 source;
- **state changed across snapshots / combat sequence context present** — T or same-turn VCR appearances show factual ownership/damage/fuel/ammunition/position transitions, capture/reinsertion or another engagement that can account for the apparent residual;
- **new Host rule remains plausible** — source alignment is clean and no additional same-turn sequence context explains the side assignment.

Only the underlying raw observations may become `CORPUS_OBSERVED`. A causal Host mechanic requires separate attributable evidence before `DIFF_VERIFIED`.

## Next work after this gate

If both residuals remain genuinely isolated with clean source alignment, continue with independent controls for:
1. matching-Friendly-Code / Harmonic Weapon Modulation boundaries;
2. dynamic multi-ship opponent selection;
3. PIA/C&I pair selection;
4. capture/reinsertion and ownership changes;
5. between-phase repair and ship-vs-planet ordering.

Game `591478` remains excluded from ordinary-mechanics tuning.
