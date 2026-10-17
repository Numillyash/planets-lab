# M2 continuation: two redacted HAR captures, 555 saves

Date: 2026-10-17. **Only aggregate descriptions and synthetic
wire-format examples appear in this document.** The real player
captures, game IDs, user-authored notes, timestamps, and private
resource CSV stay local and are not committed.

## Provenance and coverage

The player voluntarily supplied a second locally redacted client HAR
extract of 151 POST /game/save calls (all HTTP 200 and
response.success=true), 29 category-only /game/turnready calls,
zero extraction failures, and 30 game/player/turn windows.
The first capture had 404 saves, 60 readiness calls, 62 windows
and 5 different games. Combined there are **555 saves, 89 readiness
calls, 5 games and 90 unique game/player/turn windows**.
Two windows occur in both files, but no identical save event was
found across them. Each overlapping window is stitched by timestamp,
with 3 additional same-turn Starbase field changes at the seam.
Two of the five games now have 26 and 47 consecutive observed turns.

Across the two captures: **1,689 serialized records** (Note 1025,
Planet 276, Ship 197, Starbase 119, Stock 72) and **340 within-turn
reobserved field differences** (Starbase 141, Planet 95, Ship 60,
Note 44, Stock 0), with private Note.Body values excluded from
any public evidence. Of those field differences, 119 appear beyond
the first report, 3 across the same-turn capture seam.
There are no schema extraction failures and no new unknown form keys.

These are **successful client save API responses, not independent
NuHost executed order acknowledgements**. No cross-turn field delta
is attributed to a client-side user action without a separate Host
boundary witness.

## Critical correction: Starbase IDs do not equal planet IDs

Our bundle analyzer initially matched StarbaseN only to PlanetN
by suffix. This was an erroneous **identity inference**. Actual
co-submitted client saves show Starbase1 being edited with Planet8
in one game and with Planet1 in another. The starbase ID and planet
ID are independent.

The fix conservatively counts a client starbase ship-build event
only when the same POST has one IsBuilding false→true transition
and **exactly one** previously observed Planet with decreases in
MC, D, T and M. If several planets meet the criterion or any
prior resource baseline is missing, abstain. This demonstrates a
same-request cost *co-change*, not physical starbase ownership
or an isolated NuHost cost function.

This correction recovers 7 previously undercounted client
build/resource events from the original 404 save capture:
**11 in the first capture**, **9 in the second**, **20 combined**.
The original handoff had reported 11 but several cost CSV cells
were blank due to this suffix-join bug; these were recoverable
because the observed co-submitted planet was Planet8, not Planet1.

### Replicated same-request client resource deductions

| Client ship build selection | Events | MC | D | T | M |
|---|---:|---:|---:|---:|---:|
| Hull 5 / Engine 7 / Beam 8×4 / Torpedo 8×4 | 10 | 1190 | 104 | 75 | 235 |
| Hull 17 / Engine 7 / no weapons | 2 | 500 | 91 | 13 | 38 |
| Hull 16 / Engine 9 / no weapons | 2 | 365 | 20 | 7 | 41 |
| Hull 4 / Engine 9 / Beam 2×4 / Torp 4×4 | 2 | 802 | 56 | 37 | 131 |
| Hull 4 / Engine 9 / Beam 6×4 / Torp 6×4 | 2 ordinary | 902 | 108 | 37 | 135 |
| Hull 4 / Engine 9 / Beam 2×4 / Torp 6×4 | 1 | 858 | 60 | 37 | 131 |
| Hull 4 / Engine 9 / Beam 6×4 / Torp 6×4, tech update | 1 | 3302 | 108 | 37 | 135 |

The last example includes EngineTechLevel 7→10 and EngineTechUp
0→3; the extra 2,400 MC over the otherwise equal 902 MC build
is consistent with simultaneous client-side tech purchase. The
cost of each individual tech level is NOT established. Repeated
builds belong to the same local game, so these are repeated
client observations, not independent engine implementations.

## New Waypoints evidence and unchanged transfer limitations

Nonempty Waypoints appear in **10 Ship snapshots** across the
combined captures; **7** were in the second. There are **7 distinct
strings**. A representative format is the colon-delimited coordinate
sequence `2004,2035:1960,2051:2004,2035:`, including repeated
coordinates. Preserve the raw string; do not invent Host waypoint
order, move phases, or alternate delimiters.

No new nonzero TransferClans snapshots appear in the second
capture: 12 remain in the combined set, with 11 distinct
signatures and one same-turn exact cargo/pending-transfer balance
upon cancellation (20 clans + 200 MC restored to available cargo).
Two previously observed native tax vs happiness-preview changes
are also unchanged.

## Implementation and scope

- Update `nu_save_payload.py` bundle-summary logic to use a
  unique same-request Planet decline instead of equal Starbase/
  Planet numeric ID, and abstain on ambiguity or missing baseline.
- Add synthetic regression coverage of Starbase1/Planet8, two
  candidates, and a missing Planet baseline.
- Keep the latest real HAR data private; no API keys, user-authored
  notes, game IDs or actual gameplay CSV in GitHub.
- NuHost causality not promoted; C5, canonical combat, corpus CURRENT,
  production IntelBoard, external-engine analysis, and draft PR #28
  unchanged.
