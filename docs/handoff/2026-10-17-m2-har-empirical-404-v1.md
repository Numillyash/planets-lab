# M2: full HAR empirical client save dataset — 404 requests

## Provenance

The player delivered a **locally credential-redacted** HAR-derived
`planets-lab.har-save-capture-bundle.v1`, not a raw HAR. It contains
404 extracted XHR/HTTP POST `/game/save` observations (all 404 HTTP
200 and `response.success=true`), 0 extraction failures, plus a
category-only count of 60 `/game/turnready` calls from 1,773 original
HAR entries. Five distinct games and 62 game/player/turn windows.
No private source material or live game IDs are committed.

This is a *client request / positive save API response* observation.
It does not independently prove individual per-order acceptance,
NuHost phase timing, downstream execution, or Host causality.
Do not promote causal tests to `DIFF_VERIFIED`.

## Coverage and observed changes

The 404 requests include 1,161 legacy entity records:
701 `NoteNN`, 201 `PlanetNN`, 139 `ShipNN`,
80 `StarbaseNN`, and 40 `StockNN` entries.
All observed `keycount` values matched each form's parameter count;
the available records have valid `Field:::value|||...` grammar.

Comparisons with each object's most recent earlier included save
**within the same game/player/turn** reveal 221 changed fields:
78 Starbase fields, 59 Planet fields, 45 Ship fields, and 39
Note.Body changes. The changed notes are not game-engine orders and
their user-authored texts are not published.

Save requests are partial records. Never treat missing keys as
deletions. Cross-turn changes cannot be interpreted as client actions
because host processing can occur between those turns.

### Ship-to-target transfers

There are **12** saved Ship snapshots with nonzero
`TransferClans`, grouped into **11 distinct within-turn signatures**
(one identical repeated save). All carry a nonzero
`TransferTargetId` and `TransferTargetType=1`.
Nine snapshots additionally have `TransferMegaCredits > 0`.
Only the wire value '1' is verified here; target-type
semantics should be separately established, not guessed.

One particularly strong **same-turn client observation** sets and
later clears an outstanding ship transfer:
`Clans:30→50`, `MegaCredits:1269→1469`,
`TransferClans:20→0`, `TransferMegaCredits:200→0`,
`TransferTargetId:12→0`, `TransferTargetType:1→0`.
This perfectly balances the unreserved cargo and queued transfer
quantities. It is strong evidence for a **client-side pending
transfer reservation/cancellation** mechanism. It is not proof that
NuHost executed that transfer.

This is a distinct mechanism from previously owner-attested
direct planet loading, in which the client's available stocks changed.
The simulator's `PlanetCargoTransferOrder` must not conflate
directly updated client stock with a pending ship-target
`Transfer*` command.

### Starbase ship-build costs

**11** in-turn transitions to `IsBuilding:true` have a same-request
planet resource deduction in MC, D, T, M (not a Host outcome).
Replicated cost vectors for identical recipes:

| Client build selection | Observed repeats | MC | D | T | M |
|---|---:|---:|---:|---:|---:|
| Hull 5 / Engine 7 / Beam 8 x4 / Torp 8 x4 | 3 | 1190 | 104 | 75 | 235 |
| Hull 4 / Engine 9 / Beam 2 x4 / Torp 4 x4 | 2 | 802 | 56 | 37 | 131 |
| Hull 4 / Engine 9 / Beam 6 x4 / Torp 6 x4 | 2 ordinary | 902 | 108 | 37 | 135 |

An additional matching full build selection cost **3,302 MC**
while `EngineTechLevel:7→10` and `EngineTechUp:0→3` were
present in the same event. This is **+2,400 MC** relative to its
ordinary 902 MC recipe. Do not assign 2,400 to a particular
upgrade formula without an isolated experiment.

### Tax and client happiness preview

Two in-turn changes include:
- `NativeTaxRate:0→5` paired with
  `NativeHappyChange:6→2`.
- `NativeTaxRate:0→50` paired with
  `NativeHappyChange:4→-37`.

These are client-saved tax rate and happiness forecast fields,
not NuHost-verified next-turn population happiness calculations.

### Auxiliary wire-field discovery

The prior parser ignored two real field families.
`StockNN` has `Id`, `Amount`, `BuiltAmount`, with the
embedded ID matching the suffix. `NoteNN` has `Id`,
`OwnerId`, `Body`, `TargetId`, `TargetType`, `Color`.
For **Note**, the suffix encodes a target/selector rather than the
note's object ID: e.g., synthetic `Note170` can legitimately
carry `Id:::0` and `Note120` can carry `Id:::7`.
No note body contents from actual games are committed.

`src/planets_lab/data/nu_save_payload.py` now preserves both
auxiliary entity classes, retains strict ID checks for Ship,
Planet, Starbase and Stock, and exports aggregate per-kind counts.
The HAR summary also counts nonzero pending transfers,
distinct signatures, matching starbase build/resource deductions,
and tax-field changes. The CLI prints **counts only** by default.

## Follow-up / research gates

No further manual micro-experiments are necessary for this batch.
The next engineering deliverables should be:

1. Separate client-applied stock delta from pending `Transfer*`
   reservation and model orders only with an appropriate source
   witness. Do not translate a snapshot's cargo numbers directly
   into a Host transfer command.
2. Derive a bounded library of observed build recipes/costs for
   client-vs-simulator differential comparisons. Distinguish
   tech upgrades from build costs.
3. Independently align accepted saves with actual T-1 and T
   authenticated states before attributing economic discrepancies
   to Host phases.

Frozen scope remains C5, canonical combat, corpus CURRENT,
production IntelBoard, external-engine analysis branch and
draft PR #28. No real HAR or generated player gameplay CSV is
committed to GitHub or runtime-logs.
