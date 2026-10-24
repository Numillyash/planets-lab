# PR #291 — documented standard torpedo → UNALLOCATED mines conversion quote

Date: 2026-10-24. This extends the independent standard minefield lifecycle begun with PR #290, but neither module is yet wired into the HostEngine phase order.

## Documentation and rules

Primary sources:
- [Minefields: Creation and Expansion](https://help.planets.nu/minefields): standard torpedo yields, radius limits, Robot 4x, new field vs expansion/placement and race conditions.
- [Friendly Codes: Minelaying](https://help.planets.nu/friendly-codes): MD0..MD9, MDA, MDH/MDQ, miN, implicit unrestricted Lay Mines; special codes are case insensitive in actual game.
- [Web Mines](https://help.planets.nu/adv-web-mines) and [Lay Web Mines](https://help.planets.nu/mis-lay-web-mines): ordinary Crystal entitlement; normal mine conversion rate for torpedoes.
- [Host Order](https://help.planets.nu/host-order): **DOCUMENTED** order lists lay regular mines, lay web mines, mine sweeping/scooping, mine decay and minefield conflict stages. This does NOT independently verify actual engine execution nor authorize global phase integration without complete accepted inputs.

Fixed standard named torpedo families and *per torpedo* raw mines from the official table (these names are **not** component dynamic IDs):

| Family | Mine units |
|---|---:|
| Mark 1 Photon | 1 |
| Proton Torpedo | 4 |
| Mark 2 Photon | 9 |
| Gamma Bomb | 16 |
| Mark 3 Photon | 25 |
| Mark 4 Photon | 36 |
| Mark 5 Photon | 49 |
| Mark 6 Photon | 64 |
| Mark 7 Photon | 81 |
| Mark 8 Photon | 100 |
| Quantum | 121 |

For standard normal minefields, the Robotic Imperium has a documented ×4 mine laying bonus when laying as itself. The bonus is NOT applied when using miN to lay in another race's identity, nor silently applied to web-mines.

## Implementation: isolate conversion from real placement

`src/planets_lab/rules/minelaying_conversion.py` exports `quote_standard_starship_minelaying`, `MineLayingQuote`, `MineLayingQuoteAbstain` and `STANDARD_TORPEDO_MINE_YIELDS`. It is a pure **quote**, not a real ship order and not a minefield event:
- Requires exact explicit string for standard torpedo family and declared stock of 0–10,000 torpedoes (bounded local test scope, not documented fleet capacity).
- `drop_code=ALL` is an explicit internal representation of default unrestricted mine laying, **not** a literal ship Friendly Code. `MDA` also converts all held torpedoes; `MD1..MD9` convert up to 10–90; `MD0` means **up to 100**, never zero. Drops bounded by actual stock. `MDH`, `MDQ` and `MIx` are **documented** but **not supported here**: half/quarter rounding and redirecting target ownership plus bonus need their own separately sourced rules; unknown codes ABSTAIN. Source code case-sensitive canonical uppercase by intentional contract (real FCs are case-insensitive).
- Requires explicit affirmative caller preconditions: canonical table in use, non-custom modifiers, actual eligible torpedo-tube and lay mission. Web mission separately requires web permission confirmed; non-Crystal web laying and Robot4×web are not inferred. Robot×4 additionally requires confirmed same-identity ownership.
- Returns exact before/spent/remaining torpedo count and the arithmetically **UNALLOCATED proposed mine units**, and warns whether that theoretical total exceeds the documented single empty regular field maximum `max_radius²` (100 or 150 LY). It does **not** allocate excess mines to additional fields, infer field center/ID, cap, merge or discard units; even below-cap quotes are **not actually laid mines**.
- All result fields are immutable; explicit `field_created_or_expanded=false`, `minefield_allocation_verified=false`, `host_mission_accepted_verified=false`, `host_phase_order_verified=false`, `host_causal_verified=false`. No simulation of real ship inventory mutation or Host execution.

Examples: 100 Mark 8 torpedoes → quote 10,000 raw mines under normal conditions; 100 Mark 8 torpedoes with independently asserted Robot own-field bonus → 40,000 *unallocated* raw units, **exceeds** a single ordinary 150 LY field's 22,500-unit capacity, and must not be silently assigned. The previous PR #290 conditional natural decay handles only already allocated, isolated standard typed fields. The two results **MUST NOT be composed** into a Host turn without independent placement, excess-unit and phase proofs.

`tests/test_minelaying_conversion.py` covers all eleven family yields, ALL/MDA/MD0..9 boundaries, less torpedoes than FC limit, Robot×4, web eligibility, single-field capacity warning, empty stock, immutability/determinism, and refusals for unknown/custom options, bool numbers, code owner redirection, unverified preconditions. Evidence status **DOCUMENTED formula + TESTED conditional only** once exact-head PR CI green; NOT actual `CORPUS_OBSERVED` or `DIFF_VERIFIED` for NuHost field-placement execution. No on-host runtime/corpus reading in this PR.

## Next actual mechanics gap

The next substantive minefield milestone is **field placement and expansion with geometry** under documented nearest same-owner/same-type field-center selection and field capacity. Need canonical field locations and ship coordinates, full input minefield roster and documented expansion semantics, special star-cluster exclusion, terrain, friendly-code IDs, and order sequencing. Preserve ABSTAIN if missing. Minefield decay #290 can only be integrated AFTER authenticated placement/phase ordering and interaction boundary; do not use hand-picked command-as-receipt. Dense/campaign advantages, MDH/MDQ and miN must remain separate. The source code should not be connected to HostEngine or observer UI prematurely.

Project boundaries unchanged: PR #289 completed bounded PPQ observation at `CORPUS_OBSERVED` but not Host queue proof; issue #247 remains PARKED; `CURRENT` public68, prepared public100 and sealed M2 heldout32 are not accessed. No need for a Docker host test now: pytest/CI synthetic rules only. For ANY future real corpus/Host run write a single tracked `bash tools/run-*-with-evidence.sh` reusing `tools/run-with-runtime-evidence.sh` and publish sanitized evidence to separate `runtime-logs`.

Mandatory future PR workflow: fully rewrite `docs/CONTINUE_HERE.md` with actual PR number, append `docs/PR_CHANGELOG.md`, edit substantial handoff/roadmap, check final PR HEAD green and merged main push green.
