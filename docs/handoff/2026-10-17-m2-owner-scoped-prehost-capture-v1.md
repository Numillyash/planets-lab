# M2: owner-scoped pre-Host capture aggregation V1

## Context and verified precursor

The source of this checkpoint is the clean server runtime
`runtime-logs/planetary-prehost-order-capture-v1/20261016T213327Z_53206e40e5da`
from `main` commit `53206e40e5da48c0f29cad16c5eae0de78e83766`.
Its `metadata.json` Git blob `ac782e076b04a833c77d4892cc590877b356681d`
records `exit_code=0`, `source_dirty=false`, `missing_artifact_paths=[]`.
Its published `report.json` Git blob
`c59a24dca535feefa16408555bfb74b36fda2e62`
records two hypothetical phase placements, eight ABSTAIN controls,
no real NuHost orders and no independently witnessed timestamp. This is
synthetic integration evidence, not Host parity.

## Why this stage

V1 required a `TurnOrders` row for **every player in a game**, even
though each ordinary player can only attest *their own* authorized
instructions. Implicitly filling another owner's missing orders with
`PlayerOrders()` would counterfeit completeness.

`src/planets_lab/sim/planetary_owner_capture.py` introduces
owner-scoped signed records:

- `seal_owner_observation(pre_state, player_orders, captured_at_utc, key, key_id)`
  signs only ONE player's explicit `PlayerOrders`. It binds exact
  `game_id`, `turn`, owner slot and full canonical prestate fingerprint.
  It reuses V1's strict ship ownership and `PlanetCargoTransferOrder`
  validation. The other players' orders are **not emitted** in this
  owner's signed record.
- Each owner uses their own 32+-byte key; a signing key is admitted only
  for the correct owner slot, via explicit owner-keyring scoping.
  The signed statement always includes
  `server_submission_acknowledged=false`. It is an operator's local
  observation—not a `/game/save` response.
- `aggregate_owner_observations` validates every MAC, owner,
  game/turn/prestate identity, canonical order structure and
  each captured time before the *supplied* Host-start timestamp.
  The complete set of player observations is necessary: missing,
  duplicated, foreign, tampered and late captures all `ABSTAIN`.
- `simulate_owner_bundle` passes admitted `TurnOrders` into the
  already implemented `PlanetaryOrderAwareSlice` for explicitly
  hypothetical phase placements. No partial orders or simulation states
  escape upon abstention.

**Epistemic limit:** Signing one's own observation is not proof that
the NuHost API accepted the saved turn. The clock/Host-start boundary
passed by the caller is not independently verified by this code.
Even every owner signing the same initial state does not prove the
observations are complete, only that they *claim* owner-local completeness.
Do not promote this status to `DIFF_VERIFIED`.

## Sources and acquisition gap

The public Planets.nu API documentation describes `/game/loadturn`
as a way to read a turn, and `/game/save` as a way to save commands.
References:

- https://help.planets.nu/API
- https://help.planets.nu/API-game-loadturn
- https://help.planets.nu/host-order

The API docs found do not provide a verified field-level mapping of a
successful `/game/save` submission into this project's
`PlanetCargoTransferOrder` representation. **No such mapping is invented
here.** Do not submit any real game commands from research tooling.
A future *user-authorized* capture producer must independently observe
successful saves, verify exact player/turn and relevant cargo commands,
establish the trustworthy timestamp/Host window, and keep keys/savekeys
and raw payloads out of Git and runtime-logs.

There is no privileged read of other players' orders in this
implementation: cooperation from the relevant owners, or a
controlled/authorized private test environment, is required.

## Reproducibility

A dependency-free synthetic acceptance runner exists:

```bash
cd ~/projects/planets-lab && git fetch origin && git switch main && git pull --ff-only origin main && bash tools/run-planetary-owner-capture-bundle-v1-with-evidence.sh
```

The runner records only aggregate status and reason classifications,
never owner envelopes, order payloads, user credentials or signing keys.
It checks two independent owners, two placement simulations, transfer
conservation and eight fail-closed adversarial conditions. A CI subprocess
explicitly blocks `pytest` imports.

The runner is `SYNTHETIC`; it does not read the public8 corpus or any
private Planets.nu account. The corpus `CURRENT`, C5, production
`planets-intel`, external-engine branch, canonical combat, and draft
PR #28 remain untouched.

## Next substantive experiment

Obtain, with owners' authorization, **a genuinely acknowledged**
pre-Host save record with independent evidence of identity/turn/time and
a trustworthy field-level order mapping. Freeze the source observation
before looking at the next turn. Use a single controlled next-turn
comparison; abstain whenever full scope or Host ordering is unresolved.
Do not run another residual-fitting pass over the 402 public8 mismatches.
