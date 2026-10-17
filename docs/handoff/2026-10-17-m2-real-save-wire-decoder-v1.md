# M2: verified client-save legacy serialization and partial snapshot analysis

## New factual source

The owner provided a private, credential-redacted V1 capture of ten
retained XHR POST `/game/save` requests from one observed
game/player/turn. The browser counter saw **12** saves: the ring buffer
retains only the latest **10**, so two earlier saves are unavailable.
This private actual capture must NOT be added to the public repository.

Every retained request is a form object with common `gameid`,
`playerid`, `turn`, `version`, `saveindex`, the redacted
`savekey` and `apikey` and `keycount`. Variable additional keys
include `Ship6`, `Ship3`, `Ship4`, `Ship5`, `Planet1`,
`Planet3`, `Planet4`, `Planet5`, `Starbase1`.

Each entity value is **not JSON**, but a *legacy delimited record*:

```text
Ship6=Id:::6|||Name:::LARGE DEEP SPACE FREIGHTER|||Neutronium:::600|||Waypoints:::|||ReadyStatus:::0
```

The example above is structurally representative and deliberately
shortened. Fields are separated by `|||`; the first `:::` in each
field separates name and value. `Waypoints:::` demonstrates that an
empty value must be kept. There is no justified way to infer literal
`TurnOrders` semantics merely from the presence of a field named
`TransferClans` or `TransferTargetId`.

**Important correction:** `turn` is the turn number in this observed
request. It is NOT a nested JSON game-state document. That was only a
synthetic example in the previous browser-probe integration test.

## Specific observed changes across retained requests

The capture contains 9 distinct entity identities across ten requests,
and exactly three field changes between *repeatedly observed* entities:

- `Planet1.Clans`: `914 → 814` (100 fewer clans) in a later request.
- `Ship3` first appears with `Clans=100` in the same request.
  This suggests a testable loading scenario but is NOT an authenticated
  before/after transfer of 100 clans: the preceding `Ship3` stock
  value is unavailable within the retained set.
- `Ship4.TargetX`: `1965 → 2004`,
  `Ship4.TargetY`: `1956 → 2035` in consecutive saves.
  These are client saved TARGET coordinates, not proof that the
  physical ship already moved or that its target move was executed.
- `Ship6` appears after an earlier form lacked it.
  This does **not** mean a new ship was constructed: the endpoint may
  transmit only selected entity records.
- `keycount` is equal to the count of form parameters in the observed
  examples, so a one-field increase is explained by an additional
  form key; no game rule is inferred from it.

Every one of the ten retained HTTP responses was 200 with
`response.body.saveIndex=2` and **`response.body.success=null`**.
This is materially different from earlier schema-only observations
reporting a boolean true. Do NOT mark these as authenticated
application-level acknowledgements, even though HTTP transport completed.

### Observational/evidence limits

Save POST payloads are **client-submitted game data** and may contain
predicted post-click stock values. An exact accepted-order contract,
host-start witness, full-game player order coverage, and post-Host
causal matching are not established. A field omission is not a
deletion/zero/no-op. There is no inference of execution ordering among
mining, cargo transfers, taxation, or starbase production.

## Implemented source decoder

`src/planets_lab/data/nu_save_payload.py` exposes:

- `parse_legacy_entity(raw, kind, entity_id)`: strict split of observed
  `|||` and `:::` fields, preserving every field as a *string*,
  including empty values, punctuation and leading zeros. Reject
  malformed tokens, duplicate names, unsupported entities and
  mismatched wire key and embedded `Id`.
- `parse_save_body(body, http_status, response)`: strict identity,
  legacy entity decoding, optional `keycount` validation, and
  independent response tri-state (`success=true`, `false` or
  missing/`null`).
- `parse_capture(payload)`: bounds and identity consistency checks
  across one set of retained browser observations.
- `analyze_save_capture(payload)`: compare each entity with the *last
  earlier request that included this same entity*, never treating
  omission as entity deletion or a newly included entity as creation.
  Report only factual raw before/after field strings; no cargo orders
  manufactured from stocks. Response counts keep explicit-success
  distinct from null/false. Output status is strictly observational.

These functions live beside `nu_loadturn.py` but do **not** change
`GameState`, `PlanetaryOrderAwareSlice` or `TurnOrders` mapping.
No new commands are sent to Planets.nu.

## Offline command

The local-only CLI can analyze a private, voluntarily captured file:

```bash
cd ~/projects/planets-lab
PYTHONPATH=src python tools/diagnostics/nu_save_payload_diff_v1.py \
  --input /path/to/my-redacted-save-capture.json \
  --output /path/to/MY_PRIVATE_save_field_analysis.json
```

`--output` is optional; without it only aggregated counts appear in
stdout. **The optional analysis JSON contains actual game values**:
do not commit it or send it to a public `runtime-logs` branch.
The CI regression data are synthetic; no private submitted orders,
credentials or actual game ID were checked in.

## Next real differential gate

For a *controlled* Home Sector or owner-approved custom game,
observe the same `ShipN` and `PlanetN` immediately before and
after exactly one intentionally chosen cargo transfer. Capture
whether `TransferClans`/`TransferTargetId` or already-modified
`Clans` values change. Record the actual action and a distinct
pre-event baseline in an **owner-only** artifact; do not infer an
order from first appearance of a ship. Independently verify next-turn
state before attributing any change to Host.

This is client save-wire reverse engineering, not yet causal
`DIFF_VERIFIED` of NuHost economic phases.

Frozen scope: C5, canonical combat, corpus `CURRENT`,
`planets-intel` production, external-engine research branch and
draft PR #28 remain untouched.
