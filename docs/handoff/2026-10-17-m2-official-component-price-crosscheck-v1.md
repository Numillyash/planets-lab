# M2: published wiki component prices vs. client save spending

Date: 2026-10-17.

## Correction: this is a pricing lookup, not a black-box pricing problem

The owner correctly identified that the Planets.nu race hull
screen already publishes hull costs (MC, Duranium, Tritanium,
Molybdenum), e.g. https://planets.nu/#/race/1/hulls .

The official Help documents also publish cost tables for all
**default** engines, beam weapons, torpedo launchers and starbase
technology upgrades. The canonical API documents `/static/all`
as the machine-readable source of those component specs.

Sources:

- https://help.planets.nu/API-static-all
- https://help.planets.nu/starship-engines
- https://help.planets.nu/weapon-destruction-power
- https://help.planets.nu/tech-levels
- https://help.planets.nu/building-starship-hulls
- Player-supplied Race 1 hull details table (no private account
  information or raw HAR appears in this document).

**Prices are documented**, but *mapping client BuildHullId in a
particular game to the correct hull* and identifying special prices
in campaigns/custom games are separate issues.

## Three exact four-resource reconstructions

Use prices given in the cited public tables, order MC / D / T / M.
The catalog hull ID is not assumed to be equal to BuildHullId.

| Observed client recipe | Candidate hull from Race 1 table | Hull cost | Engine + weapon cost | Predicted = observed |
|---|---|---|---|---|
| BuildHullId 4, Transwarp(9), Beam2 ×4, TorpedoLauncher4 ×4 | Vendetta Class Frigate | 170/12/23/57 | 632/44/14/74 | **802/56/37/131** |
| BuildHullId 16, Transwarp(9), no weapons | Medium Deep Space Freighter | 65/4/4/6 | 300/16/3/35 | **365/20/7/41** |
| BuildHullId 17, Quantum(7), no weapons | Large Deep Space Freighter | 160/85/7/8 | 340/6/6/30 | **500/91/13/38** |

For Vendetta, component detail is:
two Transwarp drives: 600/32/6/70;
four X-Ray Lasers: 8/0/4/0;
four Gamma Bomb launchers: 24/12/4/4.

For the candidate matches, the hull's published engine mounting
count and beam/torpedo capacities are also consistent with the
selected components. Matching four cost fields strongly supports
the *candidate name*, but does NOT authenticate a particular
client BuildHullId mapping or prove independent NuHost execution.

### Important unresolved Hull5 case

Observed: BuildHullId 5 / Engine 7 / Beam 8 ×4 /
Launcher 8 ×4 with client spend **1190/104/75/235**.

The default documented weapon/engine component sum, assuming
two Quantum Drive 7 engines, is **880/62/14/178**.
The residual hull cost is **310/42/61/57**.
If one blindly equates local Hull5 to the published Nebula Class
Cruiser (**390/42/61/73**), the predicted complete ship instead
costs **1270/104/75/251**, a mismatch of
**−80 MC, 0 D, 0 T, −16 M** versus observed.

This may indicate a different local hull identity, a modified
hull/component price, a special rule, or an otherwise unobserved
in-client transaction. It is **NOT** grounds to alter the
default documented prices or to assert a specific discount.

The candidate-matching tool must therefore report **no match**
among just the supplied Race 1 reference subset, rather than
pretending that Hull5 is Nebula by suffix equality. A complete
pinned static catalog may contain other candidate hulls; the
reference subset is not exhaustive.

## Tech upgrade price is independently documented

The public starbase Tech Levels table states that advancing
levels `7 → 8 → 9 → 10` costs **700+800+900=2400 MC**,
which exactly matches the observed extra 2400 MC in the
tech-upgrade-associated build.

This is stronger than the earlier statement that an isolated
experiment was necessary to learn the standard price; it is not.
Only verifying **which rule set was applied in a specific game**,
or independently proving Host execution, remains out of scope.

## Implementation

- `published_standard_tech_upgrade_cost_mc()` encodes the
  1→10 **documented standard** tech table, with strict ranges.
- `match_published_static_hull_candidates()` independently
  checks all supplied complete catalog hulls for predicted
  *same-client-save* price equality, with slot constraints.
  It returns candidate names/IDs without claiming the client
  BuildHullId identity.
- The existing local `nu_build_cost_calibration_v1.py` now
  accepts a pinned `/static/all` JSON and matching SHA256
  **without requiring a game-specific hull mapping** for
  price-signature candidate discovery. The explicit
  `--hull-map` is only necessary to interpret a mapped
  ID as supplied external knowledge and calculate the direct
  mapped-model residual.
- Every price-signature match is labelled
  `ONE_HULL_PRICE_CANDIDATE_NOT_ID_VERIFIED` or
  `MULTIPLE_HULL_PRICE_CANDIDATES_AMBIGUOUS`, never
  `NuHost_verified`.
- Synthetic tests use publicly documented component price
  numbers with **fake catalog IDs**, independently verifying
  three exact build vectors and one deliberate mismatch.
  Neither raw game captures nor real player identifiers
  enter the repository.

**Remaining research:** test against a **full pinned** public
`/static/all` catalog (unavailable for direct download during
this pass), including `hullsall` and game-specific race hulls.
Do not silently substitute `hullsall` records for the canonical
`hulls` ID space. Match or abstain first; do not rewrite
historic owner states or the combat corpus.

No changes to C5, canonical combat, corpus CURRENT,
production IntelBoard, or draft PR #28.
