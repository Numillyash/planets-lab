# M2: offline client economic witness layer — read-only V1

## What changed

The earlier HAR parser produced only field-level deltas and aggregate
statistics. 555 owner-provided, credential-redacted client save requests
already show distinct mechanisms:

- A previously queued ship transfer was canceled. Available cargo
  increased by 20 clans and 200 megacredits, while matching
  `TransferClans` and `TransferMegaCredits` fell to zero.
  `TransferTargetId` and `TransferTargetType` also became zero.
- Some direct ship/planet cargo edits appear as changes to available
  stock, without a corresponding `Transfer*` reservation.
  Previous owner attestation identified a net 100-clan loading,
  but the first Ship snapshot was missing; do not call this an
  exact independently witnessed before/after transfer.
- `Starbase1` can co-save with `Planet8`. Never equate a
  Starbase wire number with its planet's ID.
- Client build selection (IsBuilding false→true) has repeatable
  simultaneous planet deductions. 20 comparable examples were
  found in two sessions; 10 have a repeated identical recipe/cost
  vector. A special 3302 MC example coincided with EngineTechUp=3.
- Tax changes can update client-saved happiness *forecasts*.

A typed, observational **client witness layer** is now implemented,
separate from both the canonical `TurnOrders` model and the
NuHost simulator:

`src/planets_lab/data/nu_save_client_economic_witnesses.py`

## Event types

All event records are labeled
`CLIENT_SAVE_COHANGE_ONLY_NOT_HOST_VERIFIED`.

- `PENDING_TRANSFER_STATE_CHANGE`: a repeatedly observed ShipN
  changes `Transfer*`. When available and reserved deltas exactly
  balance for every changed transfer resource, status is
  `CLIENT_RESERVATION_BALANCED`. This records *reservation state
  arithmetic*, not Host-executed transfer. Unbalanced or
  nonnumeric changes abstain from that conservation claim.
- `CO_SAVED_SHIP_PLANET_STOCK_BALANCE`: exactly one Ship and one
  Planet change the same resource by equal and opposite amounts
  in the **same save** with a previously observed state for each
  object; the Ship's corresponding pending transfer fields remain
  unchanged. Status `CLIENT_BALANCED_CHANGE_CANDIDATE`. It is
  a candidate stock cochange, **not** automatic creation of a
  cargo `TurnOrders` command. No ship baseline means no event.
- `STARBASE_BUILD_SPENDING_COHANGE`: `IsBuilding:false→true`
  and exactly one previously observed Planet with simultaneous
  decreases in MC, D, T and M. Includes the actually saved
  recipe fields, four observed spending amounts and any concurrent
  `TechLevel`/`TechUp` changes. A tech-change example is NOT
  considered an isolated base hull/engine component price.
- `STARBASE_BUILD_COST_ABSTENTION`: if the builder has zero or
  multiple qualifying planets, explicitly emit an abstention
  instead of guessing the target or the cost.
- `PLANET_TAX_PREVIEW_CHANGE`: preserves observed before/after
  tax rate and associated client-saved happiness forecast,
  without asserting the next-turn NuHost happiness result.

Missing objects in a partial request are not deletions or zero
state. `NoteN` records and private Note.Body text are NEVER copied
to typed economic events. All game values in this layer are numeric
economic details or selected nonsecret enum fields. The optional
JSON still contains owned-game state and should stay private.

## Windows, multi-HAR stitching and boundaries

The module partitions events by real (gameid, playerid,turn). It
compares entity state to the most recent earlier observation
**inside that same group only**. Two overlapping HAR files are
merged in actual timestamp order only if every timestamp is
parseable and unique: otherwise the group returns an explicit
`ABSTAIN_CROSS_HAR_ORDER_UNWITNESSED` or
`ABSTAIN_DUPLICATE_REQUEST_TIMESTAMPS` without creating
false deltas across captures. Distinct turns are NEVER chained
as if the Host did not execute.

Existing `planetary_order_aware_slice.py`,
`planet_cargo_transfer_phase.py`, the full-information
owner-bundle capture and external Host phase models remain
untouched. This V1 intentionally does **not** construct any
`PlanetCargoTransferOrder` or claim NuHost T-minus-1 acceptance.

## Reproducing with private, locally redacted bundles

From the project root with its Python package installed:

~~~bash
python tools/diagnostics/nu_client_economic_witnesses_v1.py   --input /private/save_bundle_clean.json   --also-input /private/save_bundle_clean2.json   --output /private/client_economic_witnesses.json
~~~

- The CLI displays **aggregate counts only**; it does not print
  player IDs, game IDs, friendly codes, notes, or raw payloads.
- Optional `--output` creates private numeric evidence JSON and
  refuses to overwrite an existing output.
- The two source files do not need to be sorted or combined by
  the player; timestamps inside the files determine overlap order.
- **Never commit** either original HAR, real redacted save bundle,
  resulting private JSON, or captured player notes. Keep
  credential-like fields redacted by the local HAR extractor.

CI tests use *synthetic* game entities and check positive and
negative examples of pending reservation conservation, separate
client available-stock changes, missing baselines, Starbase1/Planet8,
ambiguous costs, tax forecasts, multiple interleaved partial saves,
cross-HAR timestamps and cross-turn isolation, Note.Body exclusion,
and no credential leakage.

## Next M2 gates

Use the emitted client witness stream as immutable observations
and map only explicit separate Host-admissible orders when
authenticated pre-Host identity, complete scope, independently
witnessed Host-start time and next-turn state actually exist.
Build recipes from isolated cost witnesses and exclude
`TechUp`-associated co-spending. Do not promote
client-only observations to Host causal `DIFF_VERIFIED`.

C5, current corpus generations, draft PR #28, external-engine
analysis and production IntelBoard remain unaffected.
