# Late PPQ: exact integral Stage-1 allocations (PR #269)

Date: 2026-10-22. DOCUMENTED rules: https://help.planets.nu/queue-ppq (late regular subphase, ten or more allocated slots, Stage 1 guaranteed planetary share, Stage 2/3 lottery, RB1..RB9 order, otherwise heaviest hull). Implemented as **conditional TESTED selection quote only**, not independently verified NuHost.

## Executable scope

`src/planets_lab/sim/late_ppq_integer_stage1_allocation.py` implements `quote_integral_ppq_regular_stage1`. It accepts a complete canonical GameState with every actually-owned planet, every ordinary starbase and its queued/idle state, known queue RB code and known prospective hull mass, full fleet, explicitly asserted default PPQ and no other influencing orders, mutations or Mining Stations. No source mutation.

At the late regular stage, after an externally asserted priority subphase and provided ships are still below soft cap, computes N = max(10, soft_limit - fleet_count). For each owner p with K_p currently owned planets, calculate N*K_p/K_owned. Only cases where every share is an **exact integer** can be supported; integer quotas then sum to N with no remaining Stage 2/3 lottery slots. An owner must have sufficient queued eligible bases. Within each owner, RB1...RB9 codes precede non-RB; without RB codes, heavier hulls win. Any tie **crossing the selection cutoff** abstains instead of imposing a synthetic Host tie break.

For supported allocation returns owner counts, exact guaranteed quotas, sorted selected **base SETS**, and the N lowest unoccupied ship IDs as an unassigned **pool**. This does not assign specific IDs to starbases, build ships, spend resources, award PP or run economy. It is specifically distinct from the early free-all-bases model in #268, late priority #266/#267, and random PQ.

## Strict limitations

- Whole-turn or independent Host verification: **none**. No server-accepted orders, independent Host boundary, stage timing, external randomness or DIFF_VERIFIED; caller assertions are not evidence.
- If shares have nonzero fractional remainder, there is an empty quota, incomplete/contradictory roster, fewer queued bases than guaranteed quota, custom settings, an unmodeled priority/cloning/mining/action, no free programmatic ship IDs, or a selection-cutoff tie, the entire result is **ABSTAIN** without partial selected bases or a state.
- A unique set is not a witnessed serialized Host order. Even RB priorities inside the winner set do not authenticate which base receives which ship ID.
- Synthetic tests cover a 12:8 owned-planet split of 20 planets (6 and 4 guaranteed builds from ten regular slots), mixed RB/heavy-hull candidate filtering, invariance to roster permutation, and negative cases for missing context and random-boundary ambiguity.
- Default PPQ documentation does not independently resolve all practical rounding and late-stage timing cases. No ad hoc rounding or RNG seeded by this model.

## Next

1. Independently review PR #269 CI on exact head and post-merge main CI.
2. Connect only this uniquely selected late PPQ base **set** with complete warehouse purchases, final ships and 14-phase economy, requiring caller asserted permutation of the lowest legal new IDs; never claim Host assignment.
3. Build separate, explicitly selected late PQ regular stage conditioned on external selected base identity. Preserve no-HOST-proof restrictions and user-dependent experiment issue #247.
4. Later widen PPQ Stage 2/3 only with a separately justified model of fractional shares and actual lottery or abstain.

This scope must preserve public100, CURRENT public68, heldout32 seal, V1/V2 signed order data and unrelated C5/combat/IntelBoard. Each next PR updates entire docs/CONTINUE_HERE.md, its own docs/PR_CHANGELOG.md entry and meaningful additional docs before green CI/merge.
