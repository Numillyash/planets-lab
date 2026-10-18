# M2: automated surface-context residual triage and dual-artifact runtime evidence

Date: 2026-10-18.

## Research scope

This follows [the baseline68 observational ship/base context pass](2026-10-18-m2-public68-surface-residual-context-v1.md). The previously published **136-pair baseline68 / 3,769 owner-current planet** cohort contains exactly **11,813 both-default-deltas exact, 915 ground-only exact (surface residual), 33 surface-only exact, and 262 neither exact** across four minerals.

A full context report **has not yet been executed against the 26.65-GiB corpus**. Thus no actual association with ships, bases or ship cargo can be claimed yet. This PR reduces user interaction when the existing verified read-only analysis is run on the corpus server.

## Included functionality

**Offline aggregate postprocessor** `src/planets_lab/corpus/m2_surface_context_triage.py` and CLI `tools/diagnostics/m2_surface_context_triage_v1.py`:

- require the exact published immutable public100 SHA256, frozen 136-pair selection SHA256 and strict baseline68/heldout32 provenance;
- require all four disjoint classes for each mineral to match the previously published class counts **exactly**; reject a different sample/model;
- cross-check per-class surface residual magnitude histogram totals;
- distinguish observed own-ship same-site exposure from coordinate/ship-array **missingness** and calculate a descriptive exposure percentage only among eligible coordinate+ship-array observations;
- count exactly-one opposite ship-cargo delta **candidate** and separate explicit ship freshness vs missing `infoturn`;
- summarize explicit per-planet owner starbase co-presence, changed structure/tax controls and their qualified denominators;
- enforce **68 game-level cluster histogram entries** in every residual category, including zero-count games (fixed in the underlying analyzer);
- print a compact human-readable result and optionally write new `triage.json` with only aggregate data.

Output contains **no** game/player/ship/planet IDs, mineral stocks, raw HAR, messages or credentials. No statistical p-values are inferred from correlated mineral/planet observations. Observational co-presence or equal/opposite cargo deltas are never accepted as executed Host commands.

**One-shot server runner:** `tools/run-m2-public100-surface-context-v1-with-evidence.sh`, which invokes the actual corpus runner **only once**, then the existing strict report validator and offline triage CLI. The standard `tools/run-with-runtime-evidence.sh` publishes both aggregate-only `report.json` and `triage.json`, plus complete `gate.log` and provenance `metadata.json`, under a single run on the separate `runtime-logs` branch.

It never uploads raw TRNs, the 26.65-GiB DuckDB or locally captured user HARs. The canonical `CURRENT` remains unchanged.

## The only required future server action

After this PR is merged and its CI passes:

~~~bash
cd /root/projects/planets-lab &&
git fetch origin &&
git switch main &&
git pull --ff-only origin main &&
bash tools/run-m2-public100-surface-context-v1-with-evidence.sh
~~~

The default new artifact folder is:

~~~text
artifacts/planetary/m2-public100-surface-residual-context-v1/report.json
artifacts/planetary/m2-public100-surface-residual-context-v1/triage.json
~~~

The script refuses to overwrite existing artifacts. It must sequentially hash the immutable existing 26.65-GiB source and reconstruct the SAME 136 selected baseline68 T−1/T pairs; it does not fetch games or create another DB generation.

**No need to paste output into the conversation.** The resulting `runtime-logs` branch is sufficient. If the server run fails, do not edit `CURRENT` or raw corpus to force it; inspect the failure log.

## After actual results arrive

- First verify the category cross-tab and denominator gates are unchanged; if not, abstain.
- Quantify what fraction of the 915 observed surface residuals coincide with same-site own ships and exactly-one opposite ship cargo candidate, relative to both-exact eligible context controls. **Co-location does not establish causality.**
- Analyze positive vs negative surface residual signs with context and starbase presence.
- If data support, add bounded case-selection for independently authenticated saved orders or explicit private owner-before/after snapshots; keep game-disjoint prospective holdout32 sealed.

No changes to C5, canonical combat, production IntelBoard, existing verified database generation or draft PR #28.
