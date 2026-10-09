# 80-game combat mass survey: digest handoff (2026-10-09)

Input checkpoint: `runtime-logs/combat-long-mass-survey-v1/20261009T133620Z_21ed81470184`, clean main HEAD `21ed8147018449a3d1e1918dba9ed40cc70fb16f`, exit_code=0.

Observed: 80 games, 320 turns, 3912 ship-vs-ship VCRs, 7821 analyzed sides, 3 missing sides, 2137 non-ship VCRs. Numerical classes: 5791 baseline, 706 right +360; 524 Shield Generator candidates (145/307/38/34 by single/double and +360), 414 Horwasp full endpoints, 60 full+360, 259 partial, 52 other unexplained, 15 Horwasp/catalog conflicts. Horwasp: 187 transitions, 135 with mass change.

**Numbers are not independent prediction accuracy**: factual current VCR masses determined the numerical classes. T-1 owner snapshots do not establish combat-phase generator position or clan attrition. Repeated ship/fleet VCRs are correlated.

New code reads all 80 immutable on-disk per-game checkpoints and the existing published survey summary, without querying DuckDB. It verifies checkpoint identity, selected game-turn coverage, VCR/side/class denominators, and all published totals. Then produces ranked games/turns, a diversified selection of unresolved VCR examples, T-1 generator site/co-travel sample controls, and Horwasp changed-mass sample transitions.

**Sampling caveat**: original checkpoints retained only the first 20 interesting VCR sides and first 20 Horwasp timelines per turn. Timeline entries retain at most 40 VCR starts. Thus the per-game/turn class COUNTS are complete within the survey's 150 VCR/turn cap, but some of the 67 residual VCR identifiers are lost. The digest reports the gap, not invented identities. For complete individual cases, run a targeted corpus scan later.

Server command:

    cd ~/projects/planets-lab
    git fetch origin
    git switch main
    git pull --ff-only origin main
    bash tools/run-combat-long-mass-survey-digest-v1-with-evidence.sh

Output: `artifacts/combat/long-mass-survey-digest-v1/published/digest.json`.

Evidence branch: `runtime-logs/combat-long-mass-survey-digest-v1/`.

The old checkpoints are read-only; do not delete them yet. No Host rules, production client or probabilistic evaluator changed.
