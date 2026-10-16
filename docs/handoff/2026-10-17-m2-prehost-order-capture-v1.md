# M2 pre-Host cargo-order capture: attested intake v1

## Scope

This research-only implementation moves M2 from `TurnOrders`-only
controlled simulation toward a **provenance-gated real-order intake**.
It does **not** acquire any genuine private NuHost orders automatically
and does **not** claim historical or causal NuHost validation.

It adds `src/planets_lab/sim/planetary_order_capture.py`:

- `seal_prehost_capture(state, orders, captured_at_utc, key, key_id)`
  generates a canonical, explicitly scoped private envelope, bound to
  `game_id`, exact turn, all known game players and the SHA256 fingerprint
  of the full mechanically relevant pre-Host `GameState` (excluding metadata).
- A 32+-byte operator-controlled HMAC-SHA256 key signs the canonical payload.
  Key identifiers are public; the key must remain **out of Git, artifacts,
  logs, issue reports, and pull requests**.
- `admit_prehost_capture(envelope, state, keyring, observed_host_start_utc)`
  checks the MAC, schema, game/turn, pre-state SHA, ownership,
  ship/planet transfer type, exact signed player coverage and timing.
  It rejects missing, changed, partial, duplicate, unsigned, foreign
  or malformed records with `ABSTAIN_*`, returning no `TurnOrders`.
- An **explicit** row for every player is required, including players with
  empty submissions; `TurnOrders.empty()` alone never proves that a
  historical player submitted nothing.
- `simulate_admitted_capture` runs the **existing** `PlanetaryOrderAwareSlice`
  only after admission and returns no modeled state on admission rejection.
  An accepted record is still labeled
  `MODELED_OPERATOR_ATTESTED_NOT_NUHOST_DIFFERENTIAL`.

**HMAC is an integrity and operator-authentication primitive, NOT independent
proof of the actual orders accepted by Planets.nu.** The self-reported
`captured_at_utc` and caller-supplied `observed_host_start_utc` are
compared but the module cannot verify the witness clock/source. A capture
producer must independently establish (and privately retain):

1. Whether these were the **actual submitted** orders, not an edited client
   draft or a reconstructed order from after-the-fact cargo stocks;
2. That the entire declared set of player submissions was captured;
3. An independently trustworthy pre-Host timestamp and Host start boundary;
4. Matching full-information pre-state, and independently trusted post-state;
5. Absence or modeling of external movements, purchases, combat and other
   confounders before labeling any historical comparison causal.

Without this evidence, even a syntactically accepted HMAC cannot establish
NuHost parity. It may only support the controlled internal simulation.

## Integration surface for an owned/authorized capture producer

The trusted producer imports and calls the functions directly. It must collect
`GameState` and `TurnOrders` **before Host execution** from independently
observed records. `seal_prehost_capture` requires an explicit
`PlayerOrders` for each player in `GameState.players`, and only
`ShipOrder(planet_transfer=...)` or explicit empty player rows are
supported in V1. Other orders do not silently disappear; capture admission
must `ABSTAIN` rather than silently discarding unsupported commands.
Do not treat a post-Host `/game/loadturn` or historical
`/game/loadall` snapshot as a submitted transfer-order source.

The envelope is **private**. Do not publish its contents to the repository.
Store access-restricted and encrypted, or keep only hashes and aggregate
coverage summaries for public research. Use distinct strong HMAC keys per
capture trust domain, never the fixed synthetic key in diagnostics. Future
connector/capture hooks will need explicit authenticated authorization.

## CI and runtime

`tests/test_planetary_order_capture.py` covers operator-attested admission,
state/turn/ship-player identity, HMAC integrity, replay/mutation rejection,
pre-Host timing, missing witness/coverage, unsupported order fields, no
partial-state exposure, and both explicit `PlanetaryOrderAwareSlice`
phase placements. A separate CLI test blocks `pytest` imports entirely.

`tools/diagnostics/planetary_order_capture_v1.py` is a dependency-light
**synthetic** runner, not a source of real player orders. It uses a fixed,
public, TEST-ONLY HMAC key and synthetic 2026 timestamps to cover
two conditional placement simulations and eight `ABSTAIN` controls.
It outputs **summary only** (no submitted raw orders, envelope or private key).
The server wrapper publishes runtime evidence under
`planetary-prehost-order-capture-v1`; no corpus database is opened,
no CURRENT is accessed, C5 is frozen.

Server command after main CI:

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-planetary-prehost-order-capture-v1-with-evidence.sh
```

## Next science gate

After the dependency-free runner and GitHub tests are verified, obtain a
*separately authenticated* order capture for one authorized controlled game
and independently witness Host start. Select the capture before viewing T
outcomes and test one bounded T−1/T window. If there is no trusted source
order capture yet, the historical comparison denominator is **zero with
ABSTAIN**, not silently assumed zero orders.

C5, canonical combat, the historical public8 DuckDB, corpus `CURRENT`,
production `planets-intel`, external-engine branch and draft PR #28 stay
unchanged.
