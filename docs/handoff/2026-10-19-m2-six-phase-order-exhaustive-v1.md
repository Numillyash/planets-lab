# M2: complete six-way conditional cargo / technology / economy ordering

Date: 2026-10-19.

## Problem found after PR #240

The order-aware simulator supported two cargo-vs-planetary placements and
only two *outside* technology positions: before both or after both.
The missing two of the `3! = 6` possible orders place starbase technology
**between** the entire planetary economy block and cargo transfer.

The verified V3 public68 evidence remains unchanged: 915 residual mineral
comparisons in 315 planet windows; 108 mineral cargo coincidences
(65 single-only, 36 overlapping, 7 multiship-only); 65 cargo-associated
planet windows; 15 observed weak-linked base tech-change windows and 1
cargo/base combination. This is `CORPUS_OBSERVED` descriptive data,
not independent NuHost phase attribution. The server's prior synthetic
starbase-tech gate and PR/main CI are `TESTED`, not `DIFF_VERIFIED`.

## New bounded six-way gate

`PlanetaryOrderAwareSlice` retains its existing explicit legacy
`tech_before_planetary` / `tech_after_planetary` semantics and adds
`tech_between_cargo_and_planetary`, with no internal reordering of the
published `PlanetaryHostPipeline` block. With both cargo placements,
the complete conditional orderings are:

1. tech → cargo → economy
2. tech → economy → cargo
3. cargo → tech → economy
4. economy → tech → cargo
5. cargo → economy → tech
6. economy → cargo → tech

The explicit six-way reconciler `reconcile_all_standard_tech_phase_orders`
only executes with a genuine `TurnOrders` technology order, declared
complete orders and pre/post `GameState` snapshots, and caller-supplied
standard eligibility caps. It runs every distinct candidate, retains
per-phase MC inventory ledgers and signed observation-minus-model residuals,
and returns candidate match/ABSTAIN per ordering. It does not choose a
"true" phase order when multiple models fit, infer tech orders from
archive base changes, or equate a model match with Host acceptance.
Absent tech orders or missing completeness causes ABSTAIN instead of
meaningless six identical matches.

`reconcile_owner_observations_v2_all_tech_phase_orders` performs exactly
the same experiment only *after* verifying complete HMAC owner records for
all players, the prestate fingerprint and caller-supplied Host-start
boundary. A private signature authenticates only its operator's record.
It does not independently witness an external Host clock or execution.
V1 capture remains unchanged and rejects technology records.

Deterministic CI scenarios verify six phase sequences, exact tech cost,
cargo-funded tech feasibility, signed residuals, no-order/snapshot/cap
rejection, tampered owner records and no causal status promotion. This is
code-only and synthetic: no corpus DB, private captures, `CURRENT`,
heldout32 entities, C5/combat, or IntelBoard processing.

## Next evidence dependency

A genuinely attributable NuHost `DIFF_VERIFIED` transition still needs
independently verified submitted orders (including the selected base upgrade
and transfer), complete pre/post state, certified timing and an observed
server outcome. None of these can be conjured from the 68-game public
aggregate or locally signed fixture. This phase **does not require the
owner to conduct a new game experiment**.
