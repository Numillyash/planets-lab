# M2 Host differential: local readiness versus independent causal evidence

Date: 2026-10-20.

## Completed evidence

The published synthetic client-sequence runtime at
`runtime-logs/m2-client-sequence-audit-synthetic-v1/20261020T135946Z_98d857cc3b62`
has `exit_code=0`, a clean checkout and exact source
`98d857cc3b62ae1a3a7eb678141b1ab878fceca1`.
The Node -> atomic client metadata bundle -> independent Python
consistency audit classified a *fictional* record containing one
save/ready candidate, one ready without a fresh save, zero dropped
events, and no server/execution provenance. This completes a synthetic
software check, **not a NuHost differential**.

The V3 historical corpus (68 baseline games, 136 selected transitions)
and all prior synthetic phases remain unchanged. Public historical
loadall cannot recreate complete player order submissions for T-1,
independent Host accepted order receipts or full private owner-current
snapshots for all declared game players.

## New local-only readiness admission

`src/planets_lab/sim/planetary_host_differential_readiness.py` composes
existing M2 evidence checks as a **pure, privacy-restricted** function:

1. Validate a bounded adjacent `GameState` pair, including roster,
   unmodeled ship state and known starbase identity controls. This only
   tests structure: it does not independently prove snapshot origin or
   visibility/completeness.
2. Require an explicit *operator assertion* that both snapshots have
   complete coverage. This is insufficient for external provenance.
3. Authenticate *all* owner-scoped V2 HMAC envelopes against the exact
   T-1 state and caller-supplied pre-Host time. These are local operator
   records: signatures do not attest server receipt or accepted orders.
4. When actual technology upgrade orders and standard eligibility caps
   are present, run the existing six conditional cargo/tech/economy
   placements. When technology orders are absent, use the existing
   cargo/economy differential; unsupported starbase contexts ABSTAIN.
5. Optionally recompute a same-source atomic client metadata bundle's
   strict trace/count consistency. Never correlate that bundle to the
   signed game orders: **it carries no game or order identities**.

The result contains only fixed statuses, counts and three fixed
**unresolved external blockers**. It returns neither state/order
contents, owner IDs, game IDs, timestamps, HMAC tags/keys, hashes nor
resource residuals. There is deliberately no `DIFF_VERIFIED` outcome:
a source-independent server accepted-order witness and credible
complete pre/post source and Host boundary are *not implementable*
by trusting three caller-provided boolean fields or a local HMAC.

`LOCAL_CONDITIONAL_COMPATIBILITY_NOT_NUHOST_VERIFIED` means only that
some supported model placements equal the **locally supplied** poststate.
It is a compatibility hypothesis, not proof of which ordering actually
ran or even that the submitted data ever reached NuHost.

## Remaining information that cannot be synthesized

The next real causal study needs a controlled game transition in which
all relevant participants voluntarily provide (a) their actual full
orders for one identified pre-Host turn, (b) an independently checkable
record that these specific orders were received/accepted by the
server before processing, and (c) suitable complete, dated owner-current
pre- and post-Host snapshots and an independent Host-time witness.
A single player's client `/game/save` success does **not** provide
these conditions for a multiplayer turn.

If the users cannot obtain independent server acceptance evidence,
the research must remain `TESTED/CORPUS_OBSERVED` or a clearly
`CONDITIONAL` model comparison, not `DIFF_VERIFIED`. Collect only
consensual game observations and retain all private records outside
the public Git repository and `runtime-logs`.

## Verification scope

Deterministic tests verify local owner signatures, the bounded
state checks, model compatibility counts, malformed/tampered orders,
missing asserted snapshot coverage, missing tech eligibility, and
an unconditional noncausal outcome. This is **code-only** validation:
no 26.65-GiB corpus pass, heldout32 entity data, private files,
external network, C5 combat or production IntelBoard changes.
