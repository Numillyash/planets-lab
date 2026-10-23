# Pull-request project-state and continuation log

This is the **durable per-PR summary** for new chats and future maintainers.
Starting with PR **#262**, **every PR** must add/update an entry
with its actual PR number, update [CONTINUE_HERE.md](CONTINUE_HERE.md)
with a copy-ready full continuation prompt, and update at least one
additional meaningful repository document. GitHub CI enforces this through
`tools/check_pr_handoff.py`. See [WORKFLOW.md](WORKFLOW.md) and
[`AGENTS.md`](../AGENTS.md).

Do **not** guess merged commit SHAs or claim a workflow is green until
GitHub confirms it. Check live `main`, PR state and workflows separately.

## #283 — Noncausal observed owner-current ship/base/planet identity intersections on frozen PQ windows (2026-10-23)

- **Real corpus evidence:** `runtime-logs/pq-window-selection-g620917-p1-from1/20261023T103725Z_15f627933064` shows 5 truly consecutive embedded PPQ windows, each with exactly **one uniquely planet-linked, owner-current and base-current starbase**. The archived base lacks direct `ownerid` but has fresh `infoturn`, unique owner-fresh planet and `buildhullid`/tech-level field **presence**, never verified actual build orders or PP warehouses.
- Added `pq_observed_transition.py` emitting bounded, privacy-minimal intersection of uniquely typed fresh owner-owned planet, ship and starbase IDs across the already admitted T−1→T window, as `observed_owner_transition` in existing `pq_window_field_sufficiency.py`. Reports only matched, newly visible and no longer visible **counts**, unknown/duplicate/missing source qualification. No individual IDs, source values or private field contents. If missing arrays or duplicate identities, observational qualification explicitly ABSTAINS. All new-ship-is-build, disappeared-ship-is-loss, global fleet completeness, component warehouses, PP and Host execution flags are **FALSE**.
- Synthetic/adversarial tests cover source provenance, duplicated ship/base/planet IDs, missing/unknown freshness, invalid embedded turns and leak exclusion. Evidence `TESTED` for new code until real auto evidence from existing `bash tools/run-pq-window-selection-with-evidence.sh`. Public original 5-window structural inference remains `CORPUS_OBSERVED`, not `DIFF_VERIFIED`.
- Full [continuation](CONTINUE_HERE.md), [technical handoff](handoff/2026-10-23-pq-observed-owner-identity-transitions-v1.md), roadmap updated; check exact-head PR CI and post-merge main CI before claims. Next real one-command corpus rerun and observational multi-game coverage.
## #282 — Owner provenance of archived PPQ starbases through unique fresh planet links (2026-10-22)

- **Real source evidence:** predeclared game 620917/p1 in `runtime-logs/pq-window-selection-g620917-p1-from1/20261022T185133Z_412db3d34b32`: 7 inspected archive-adjacent pairs, 5 embedded game.turn-consecutive, one repeated and one skipped forward. The five accepted pairs have arrays of 80 planets, one visible starbase, direct base owner-current count **zero**. Changing visible ship count is **not** independent proof of builds. `nu_loadturn._starbase` can resolve missing base owner from linked planet; previously this link was not measured by PQ diagnostic.
- New `pq_starbase_observability.py` joins each observed starbase's unique typed `planetid` to exactly one visible **owner-current planet** `id`, enforces no conflicting explicit base owner and separately requires **base infoturn=current embedded turn** to count a current linked base. Counts linked-owned-but-unknown base freshness, stale base infoturn, owner mismatch, duplicate IDs and unknown fields without fabricating positive queue states. Only static allowlisted source-key **presence counts**; no entity values/private fields.
- Wired into `pq_window_field_sufficiency.py` so the **existing** `bash tools/run-pq-window-selection-with-evidence.sh` automatically publishes expanded before/after source shapes to separate `runtime-logs`; no new host manual JSON transfer. Adversarial synthetic tests check uniqueness, stale/unknown, conflicting ownership, direct/missing base owner, PII omission and integrated two-member reader.
- **Evidence:** five real archived *structural* windows `CORPUS_OBSERVED`; new link interpretation **TESTED conditional** until source corpus rerun. No complete PP warehouses, build orders or NuHost parity. Updated [full continuation](CONTINUE_HERE.md), [handoff](handoff/2026-10-22-pq-starbase-owner-planet-link-v1.md) and roadmap. Verify exact CI/merge/main CI live.
- Next: inspect actual new `runtime-logs` rerun; build bounded field-level sufficiency by trusted, uniquely linked base and owned ship, not synthetic Host causality.

## #281 — Strict bounded automatic PQ archive-window selection after real nonconsecutive embedded turns (2026-10-22)

- Read actual published runtime evidence `pq-public-window-g620917-p1-t1/20261022T183106Z_0a3c034f1fac`: source main `0a3c034f...`, genuine failed gate `embedded turns are not consecutive` and successful automatic evidence push. Filename T1→T2 is **not** a proven game.turn T→T+1 pair. Never weaken the existing strict window reader.
- New `pq_bounded_window_selection.py` + CLI checks up to 48 filename-adjacent windows of one **frozen permitted** game/player perspective (no other ZIP/member scan), verifies embedded game/player identities and game.turn delta exactly +1, aggregates repeat/backward/forward-skip and other safely classified failures, and returns up to five sanitized valid field-shape reports. The single-window original remains fail-closed; diagnostic-only nonconsecutive inspection never returns a Host-comparable window.
- New `bash tools/run-pq-window-selection-with-evidence.sh` invokes Docker `lab` without build and existing `run-with-runtime-evidence.sh`, publishes sanitized report plus success/failure log to separate immutable `runtime-logs`; no manual chat logs/keys/raw .trn. Tests include synthetic nonconsecutive patterns, skipping to a verified window, immutable allowlist, scope limits, no source leaks and bash syntax.
- **Evidence:** prior real archived ABSTAIN observed, new selection logic `TESTED` synthetic until a new on-host published run. No accepted orders, PP warehouse completeness, host scheduling or `DIFF_VERIFIED`. Updated [full continuation](CONTINUE_HERE.md), [handoff](handoff/2026-10-22-pq-bounded-embedded-turn-window-selection-v1.md), roadmap; live exact-head PR CI, merge and main CI must be rechecked.
- Next: inspect real scanner publication and then build an observational field-sufficiency gate over predeclared windows; #247 for causal Host verification.

## #280 — Correct PQ archive/embedded turn identity and one-command sanitized runtime publication (2026-10-22)

- On actual approved game 620917/p1/archive T1→T2 PR #279 probe returned `embedded game/turn/player identity mismatch` (real server result; exact root cause within live payload pending rerun). Mature `corpus/normalizer.py` distinguishes filename archive turn and `game.turn`. #280 now verifies exact typed game/player identity plus **two consecutive embedded turns**, reports both embedded turns and constant offset and evaluates owner-current `infoturn` against embedded turn. No blanket acceptance of mismatched identities and no causal Host claims.
- Added permanent single-command `tools/run-pq-public-window-with-evidence.sh` (default approved 620917/1/T1; optional three arguments) invoking `tools/run-pq-public-window-gate.sh` with prebuilt Docker `lab` and reusing `tools/run-with-runtime-evidence.sh` for immutable sanitized runtime logs + report upload to separate `runtime-logs` branch, **including failed gates**. No manual output transfer or push onto source main, no private content/credentials included.
- New synthetic positive tests for offset -1/+1/+4 and fresh rows, adversarial nonconsecutive or foreign game/player, shell launcher syntax and wrapper usage. This CI is synthetic and doesn't independently prove the live mismatch is solved until a new host run is uploaded.
- Updated full [continuation](CONTINUE_HERE.md), [technical handoff](handoff/2026-10-22-pq-runtime-evidence-turn-offset-v1.md), workflow and roadmap. Each future host/corpus run should have a one-command tracked `tools/run-*-with-evidence.sh` publishing sanitized artifacts automatically via existing wrapper. Check actual exact-head CI/merge/main CI live.
## #279 — Bounded public PQ/PPQ T−1→T window source-field sufficiency (2026-10-22)

- Added `pq_window_field_sufficiency.py` and CLI: given EXISTING feature-index Parquet, fully explicit frozen allowed cohort (new tracked public-control12 selection: 12 existing finished games, 8 PPQ + 4 Classic controls, no M2 holdout), game ID/owner perspective and adjacent turns, recalculate #278 observational admission BEFORE touching a ZIP. Then read **exactly two** selected .trn members from ONE cached public game archive, not all members or a 26+GiB rescan. Validate embedded identity, duplicate member names, bounded plain/gzip JSON and explicit malformed/absent source.
- Emit only typed per-perspective `planets`/`starbases`/`ships` array presence/counts, explicitly owner-owned **and fresh** infoturn rows, separate owner records with absent infoturn (unverified freshness), unknown/malformed rows and missing-array reasons. Do NOT output emails, savekeys, messages, names, coordinates, source records, accepted orders or resources. Test with synthetic ZIP, gzip and adversarial private fields; malformed windows fail closed without overwriting prior report.
- Evidence strictly `PUBLIC_ARCHIVE_TWO_MEMBER_SHAPE_ONLY_NOT_DIFF_VERIFIED`; PP/component stock completeness/global roster/Host phase/order acceptance all remain explicitly false. This tests **source observability**, NOT queue mechanics parity or actual archive runtime execution. On current PR there is no claim that approved public68 ZIP members were read at CI.
- Updated complete [continuation](CONTINUE_HERE.md), [technical handoff](handoff/2026-10-22-pq-two-member-archival-window-v1.md) and roadmap. Verify final PR CI/merge and post-merge main CI live before claims.
- Next: run on **predeclared allowed** 12-game/public68 archive windows if runtime available; then provenance-qualified aggregate field-sufficiency and bounded observational queue transition audits. No heldout32 or public100 rebuild.

## #278 — Explicit frozen-cohort public PQ/PPQ historical readiness triage (2026-10-22)

- Begins **corpus-based validation preparation** after #277's local PQ/PPQ queue/economy integration: new read-only `pq_historical_readiness.py` checks typed actual PQ/PPQ game settings and archive/adjacent-turn coverage of an **explicit, immutable, predeclared allowlist** in the EXISTING feature-index Parquet. Outputs classified PQ, PPQ, excluded/unknown/not-indexed, observational metadata candidates, provenance hashes and unmet Host causal prerequisites. CLI `tools/diagnostics/pq_historical_readiness.py`; invalid/missing inputs fail closed without overwriting reports.
- No archive member/turn read or live API, no public100 rebuild, heldout32 access, CURRENT mutation or claimed observed game parity. Synthetic + deterministic Parquet tests cover settings contradictions, unknown typed fields, incomplete archives, sealed-cohort exclusion, invalid duplicate IDs and atomic output.
- This alone is NOT a historical shipyard mechanics comparison; **only observational eligibility metadata** and `host_causal_verified_games=0`. Field sufficiency of owner-current before/after ship/base/PP/warehouse and authenticated orders remains open; issue #247 for human dependent true Host validation.
- Full refreshed [continuation](CONTINUE_HERE.md), [topic handoff](handoff/2026-10-22-pq-corpus-readiness-v1.md) and roadmap, plus durable command/runbook for scoped existing index and frozen cohort. PR exact CI/merge/main status must be re-queried before claiming.
- Next: allowed public cohort PQ/PPQ per-turn field-sufficiency gate and bounded observational contradictions (no unnecessary 26+GiB scan).

## #277 — Atomically composed capped PQ wait, externally supplied loss, one rebuild and existing-fleet logistics (2026-10-22)

- New `late_pq_mixed_calendar.py` composes existing #273 waiting economic-only at SOFT cap (2–8 turns), #272 **strict full preturn snapshot** externally asserted equal to previous modeled state MINUS exactly one inert cargo/ammo-empty ship, #271 one externally selected ordinary regular build using lowest free ship ID and exact BOM/warehouse/PP/14 economic phases, then #276 2–6 capped existing-ship cargo/full normal move and intact planetary economy turns.
- Enforces that at ship-only loss boundary the entire previous ordinary base queue/idle, blueprint and hull-rights roster remains unchanged. All base inventories and owner PP are carried from prior exact ledgers, never silently replenished; normal queued ships cannot build while capped. Any later stage uncertainty → **whole-calendar ABSTAIN** with no interim world, receipts or balances.
- Synthetic full-history tests cover 2 wait → 1 externally asserted inert loss → 1 rebuild → 2 full-cap cargo/movement, explicit alternative build-economy ordering, strict ship identities, owner PP, all warehouse and resource/event ledgers, extensive negative/forgery boundary cases.
- Evidence only `TESTED conditional`; no independent NuHost combat/recycling, accepted orders, phase timing, PQ random selection or `DIFF_VERIFIED`. Update full [continuation](CONTINUE_HERE.md), [technical handoff](handoff/2026-10-22-pq-mixed-wait-loss-build-fleet-v1.md) and roadmap. CI/merge/post-main outcomes must be checked live before being claimed.
- Next: multiple independently sourced loss/build windows or real accepted Host boundary verification (issue #247); no current public100/heldout32/CURRENT changes.

## #276 — Soft-capped ordinary PQ: existing-fleet cargo/movement across fully audited economic turns (2026-10-22)

- Added `late_pq_capped_existing_fleet_cargo.py` composing #273 exact no-ordinary-build at soft cap with 2–6 consecutive existing-ship load/unload/move and complete planet 14-phase economy turns. Every ordinary queued base/idle and hull rights declared each turn; full PP and component warehouses persist unchanged. Requires one explicit `ShipOrder` for **every** existing ship/owner each turn: one ordinary non-special supported mover with unchanged armament/ammunition and all other ships fully inert.
- Independent checks reuse `_audit_transfers_and_undo`, `_planet_ledgers`, `_exact_ship_fuel_ledgers`, exact `plan_full_normal_move` and typed final ship identity; verified cargo/planet conservation, fuel burn, unchanged all other ships, IDs, owner starbases, zero normal builds, two economic phase-placement hypotheses. Any failure including on later turn abstains whole sequence.
- Synthetic positives exercise fuel/supply loading then carried-fuel follow-on move, queue changes at full cap, PP and all warehouse preservation. Negative and forged-event/resource/ship tests enforce atomic ABSTAIN. Evidence `TESTED conditional` only; no independently accepted NuHost orders, timing or parity.
- Full continuation prompt, [topic handoff](handoff/2026-10-22-pq-capped-existing-fleet-cargo-v1.md) and roadmap updated; exact-head PR CI/merge and post-merge main CI must be queried live before being claimed.
- Next mixed wait/loss/build calendar or independently bounded multi-ship logistics, not speculative NuHost RNG.

## #275 — PQ new ship load/move on separately audited following economy turn (2026-10-22)

- Added `late_pq_new_ship_next_turn_move.py`: unlike #274's hypothetical same-turn postbuild movement, #275 models **T build+full 14 economic phases**, then a distinct **T+1** normal cargo/fuel loading and full ordinary move with a SECOND complete 14-phase economic block, under two explicit next-turn placement hypotheses.
- Uses #271 exact selected single ship BOM/warehouse/PP and existing normal movement/planet cargo transfer phases plus strict receipt/delta `_audit_transfers_and_undo`, `_exact_ship_fuel_ledgers`, `_planet_ledgers`, and independent full-move fuel quote. No other ships/movement/normal builds, external interturn state mutation, priority/cloning/mining station or unsupported encounters. Atomic two-turn ABSTAIN on any missing or inconsistent input/receipt.
- Synthetic tests cover 2×2 placement variants, complete 2-turn inventory and PP carry, loaded fuel and supplies, missing context/invalid candidate moves and adversarial forged movements or planetary events.
- Only `TESTED conditional`, no server accepted orders, authenticated interturn boundary, NuHost phase positions or causal Host parity.
- Updated [full continuation](CONTINUE_HERE.md), [topic handoff](handoff/2026-10-22-pq-new-ship-next-turn-movement-v1.md) and roadmap; exact final CI + merge + post-merge status must be verified from live GitHub. Next: integrate at-cap waiting turns with ship movement/cargo without invented regular builds.

## #274 — New late PQ ship orbital load and conditional short normal move (2026-10-22)

- Introduced `late_pq_built_ship_cargo_move.py`: compose audited #271 selected ordinary ship build + complete warehouse/BOM/14-phase economy with caller-asserted postbuild **planet-to-new-ship orbital fuel/cargo loading and one short full normal movement** using existing transfer and movement phases. No second model turn or second economy calculation.
- Independent exact one-transfer order↔event, all planetary cargo debits and ship cargo credits, prediction-based fuel/position and movement receipt, immutable old ships/base/PP/warehouses, complete final game delta; unsupported route/foreign planet/combat/special/partial fuel/unknown ordering → atomic ABSTAIN.
- Synthetic tests include both conditional build/economy placements, fuel and cargo, missing rights/resources/selection, invalid phase assumptions and adversarial forged event/inventory checks.
- **Only TESTED conditional**. True NuHost Host ordering/acceptance, whether the newly built ship can move this same turn, and external parity are **not established**. No heldout or CURRENT changes.
- Updated full [continuation](CONTINUE_HERE.md), [topic handoff](handoff/2026-10-22-pq-built-ship-cargo-move-v1.md) and roadmap. CI and merge outcomes need confirmation from GitHub on the exact final HEAD. Next: safer next-turn newly built ship movement or mixed late-PQ calendar.

## #273 — Full soft-cap PQ no-build multi-turn economy and unchanged warehouses/PP (2026-10-22)

- Added `late_pq_capped_no_build_carry.py` for the **distinct** case from #272 with fleet ALREADY AT ordinary PQ soft cap and **NO** external ship loss. Runs 2–8 consecutive *economy-only* turns with a complete all-base queued+idle roster, two+ queued candidates and explicit absence of all priority pbN/clone/Mining Stations/other actions. Not a general automatic Host no-build oracle.
- Never consumes any queued ship, builds a ship or allocates an ID; owner PP and ALL base warehouses remain exact and unchanged. Runs intact 14-phase planetary economy each modeled turn, independently auditing every per-planet resource/event ledger and exact fleet/owners/stars/metadata retention. Any mismatch ABSTAINS the whole sequence atomically without partial results.
- Synthetic coverage: two different queued roster configurations at full cap, eight-turn economy/PP/stocks carry, malformed owner/rights/warehouse/cap/queue cases and adversarial forged ship/planet/event output.
- Updated complete [PR #273 continuation](CONTINUE_HERE.md), [technical handoff](handoff/2026-10-22-late-pq-capped-no-build-carry-v1.md) and roadmap. Exact PR CI and merge/post-merge main outcomes must be verified live.
- Evidence: `TESTED conditional`, NOT independent no-build NuHost selection/timing or `DIFF_VERIFIED`. Next combine explicit-loss and capped no-build temporal cases or bounded shipyard+movement/cargo integration; actual Host proof issue #247.

## #272 — Conditional multi-turn late PQ with exact externally supplied ship-loss snapshots (2026-10-22)

- Added `late_pq_external_loss_multiturn.py` to compose **2–6** successive #271 late PQ single-slot ordinary builds, carrying full owner PP and every base's warehouses, queued rights, source economy and sorted per-turn selected lowest free Ship ID. Host PQ winning base remains caller asserted, never reproduced by RNG.
- At the soft cap after EACH build, a next build must NOT be fabricated: accepts only a supplied complete external preturn snapshot **identical to prior model result EXCEPT removal of exactly ONE identified inert cargo/ordnance-empty ship** with explicit external-event assertion. No combat/recycling attribution; snapshots are caller assertions, not independently authenticated evidence.
- Each turn reuses #271 independent typed BOM/warehouse/ship, full 14-phase planetary economic resource and event audit. Any later malformed warehouse, PP change, extra ship/planet mutation, missing loss or selection causes the **whole sequence** to ABSTAIN without intermediate states, receipts or sidecars.
- New synthetic tests include consecutive turns 9→10 then external 10→9 then 9→10, ship ID reuse, warehouse stock depletion, two economic placements, loss and inventory forgery. Evidence only `TESTED conditional`, NOT real NuHost acceptance, loss, RNG, timing or `DIFF_VERIFIED`.
- Changed standalone [continuation prompt](CONTINUE_HERE.md), [technical handoff](handoff/2026-10-22-late-pq-external-loss-multiturn-v1.md) and roadmap. PR CI/merge/post-merge CI must be independently checked live.
- Next: bounded shipyard+movement/cargo integration or explicitly no-build-at-cap multi-turn branch. User-dependent Host evidence stays issue #247.

## #271 — Externally selected late PQ regular ship and full economic ledger (2026-10-22)

- Added `late_pq_external_regular_economy.py` to handle exactly one late PQ vacant soft-cap ship slot with two or more competing queued ordinary bases; **winning base is explicitly externally caller-asserted**. The NuHost PQ random selector or RNG is NOT modeled or claimed causal.
- Enforces complete 2–64 ordinary base roster, warehouses even idle and unselected, full owner PP, valid hull rights, lowest available ship ID, no priority/clone/mining/movement/combat; builds exactly one selected ship with independently audited BOM, warehouse and source material spend. Full 14-phase planetary economic/resource/event ledgers and final ship identity for two conditional economy placements; normal PP unchanged.
- Synthetic positive cases: both placements, alternate externally selected winners, stocked components avoid planetary material spending; negative and forensic cases require atomic ABSTAIN. Evidence level strictly `TESTED conditional`; no real host accepted order, random selection or phase order.
- Full PR #271 [continuation prompt](CONTINUE_HERE.md), [topic handoff](handoff/2026-10-22-late-pq-external-regular-ship-economy-v1.md) and roadmap updated. CI/merge must be verified live on final head.
- Next: optional multi-turn PQ with externally supplied selections and full sidecar carry, or scoped shipyard+movement integration. No heldout/corpus changes.

## #270 — Late PPQ integer-share Stage-1 ships, warehouses and 14-phase economy (2026-10-22)

- Added `late_ppq_integral_stage1_economy.py` on top of #269's exact integral quotas: one complete warehouse and queued-ship blueprint/hull rights for each of the fully enumerated starbases (including unselected), and explicit selected-base-to-ID caller permutation of exactly N lowest available 1..999 ship IDs.
- Complete **ten** ordinary ships can cross PPQ's soft ship limit; source component assembler's separate programmatic `999` ID ceiling is used instead of treating soft cap as hard. Per-ship independent material+BOM ledger, all-planet 14-phase economic events/resources, complete unchanged per-owner PP, unchanged old fleet and unselected warehouses, and strict final ship identity verification.
- New synthetic positive tests cover 19→29 fleet at softcap20 (6+4 exact owner builds), two economic placement hypotheses, swapped explicit IDs, full stored components; negatives reject forged economic events and complete-roster/inventory/scope violations atomically.
- Updated standalone [full continuation prompt](CONTINUE_HERE.md), [topic handoff](handoff/2026-10-22-ppq-integral-stage1-ship-economy-v1.md), roadmap; PR CI/merge outcome is NOT claimed before checking live GitHub.
- `TESTED conditional` only; no server-selected base identity, true NuHost ship ID ordering, Host accepted orders, phase order or DIFF_VERIFIED. Next separate late PQ external-selected regular build/economy.

## #269 — Exact owned-planet integral PPQ Stage-1 regular selection (2026-10-22)

- Added `late_ppq_integer_stage1_allocation.py`: complete late PPQ normal-slot selector, N=max(10, soft-cap gap), exact per-owner integer share of **owned** planets. Only when all guaranteed quotas are integers do they exhaust N without Stage 2/3 lottery; require queued candidate capacity per owner.
- Deterministic base SET chosen from RB1..RB9 then heaviest hull. Tie crossing quota boundary or unknown hull/RB/incomplete fleet/planet/base roster results in whole-quote ABSTAIN. Return N lowest unused ship-ID pool but **do not assign IDs to selected bases**, construct ships, spend resources or invent NuHost order.
- Synthetic tests include 12:8 owned worlds → six/four of ten slots, RB ordering, hull-mass fallback, permutation invariance, 24 malformed/ambiguous cases.
- Evidence is `TESTED conditional` only; external server orders, lottery, Host phase timing, stage 2/3, generic rounding and causal acceptance are **not** verified. No heldout corpus touched. Next: connect unique PPQ selected SET to audited complete warehouse/14-phase economy under caller-asserted ID permutation; separate external selected late PQ branch.
- Updated [PPQ handoff](handoff/2026-10-22-late-ppq-integral-stage1-allocation-v1.md), roadmap and full continuation prompt. PR CI/merge not claimed before independent GitHub check.

## #268 — Early unthrottled PQ/PPQ ordinary builds and idle starbase PP (2026-10-22)

- Added `early_pq_ppq_idle_pp_turn.py`: complete 2–64 ordinary starbase roster including at least one regular queued build and at least one idle selected base, far below 90% of configured soft ship cap. Standard shipbuilding spends 0 PP; each selected eligible idle base earns exactly +2 default Priority Points assigned to its owner. Does not model Mining Stations, custom idle PP earning rules, pbN, cloning, unknown combat or regular late queue contention.
- Unlike the previous all-queued #258 slice, this model validates warehouses for idle bases as well as active bases; assembled ships use the exact lowest-N unoccupied ship-ID **set**, while base-to-ID assignment remains only caller-asserted since real PQ/PPQ can randomize ordering. Reuses component/warehouse audit, independent final ship identity, full 14-phase economy and per-planet resource/event ledgers, with whole-turn ABSTAIN on unsupported inputs.
- New tests: PQ and PPQ × 2 economy placements; 2 queued/1 idle with +2PP, 1 queued/2 idle with points for both owners, zero-MC stocked ship, tax-funded late building, permuted ID assignments, low-ID set rejection, phantom idle stock, false/duplicate owners and forged final states.
- Updated [roadmap](ROADMAP.md), [topic handoff](handoff/2026-10-22-early-pq-ppq-idle-pp-v1.md) and [full continuation prompt](CONTINUE_HERE.md). PR CI/merge outcome is not claimed until GitHub verifies it.
- Remains `TESTED` conditional only, with external real NuHost causality parked in #247. Next: late PQ randomized normal allocations vs separately PPQ owned-planet share and RB# slots.

## #267 — Late PP-funded PQ/PPQ priority ship and 14-phase economy (2026-10-22)

- Extended #266 beyond a default PP quote: `late_pq_ppq_priority_ship_economy.py` constructs the single, fully asserted `pb1` priority ship **after configured soft cap** but before the programmatic 999 ship-ID ceiling. It reuses the #257 independently checked BOM, warehouse and full typed new-ship auditor.
- Owner PP is separately charged by the documented default quote; only missing purchased components debit planetary MC/minerals. Unmodified 14-phase planetary economy runs before or after priority ship construction under two explicit conditional hypotheses. Strict final-ship identity, old-ship/base immutability, and full independent event/resource ledgers; unsupported conditions ABSTAIN without partial state/PP.
- Synthetic tests cover both PQ and PPQ × two placements, 8->9 beyond softcap, full warehouse zero-resource build with still-charged PP, tax-funded after-economy costs, 1100KT 21PP, adversarial forged ship/ground/tax and invalid owner/queue/stock cases.
- Updated [topic handoff](handoff/2026-10-22-late-pq-ppq-priority-economy-v1.md), [roadmap](ROADMAP.md) and complete [new-chat prompt](CONTINUE_HERE.md). PR CI and main merge success must be checked live before claims.
- Does not implement randomized PQ or planet-proportional PPQ regular late queue, RB# selection, PP awards or real NuHost Host order. Evidence `TESTED conditional`; #247 still parked.

## #266 — Late PQ/PPQ single priority admission and PP quote (2026-10-22)

- Added `late_pq_ppq_priority_admission.py` with the **default** PQ/PPQ PP formula `1 + ceil(min(hull_mass_KT,1000)/50)` (2 PP for 50KT, max21). Only one explicitly `pb1`-coded late request against a complete base/fleet and owner PP roster is admitted; every other base idle, soft cap already reached, global programmatic IDs below 999.
- Reports model-only lowest available ship ID and owner-specific PP after a conditional build; DOES NOT build a ship, alter economy or assert NuHost selection. Custom cost, competing pb2/ordinary priority/regular builds, ownership discrepancies and missing roster ABSTAIN.
- Added deterministic PP arithmetic and negative source/queue tests, [technical handoff](handoff/2026-10-22-late-pq-ppq-priority-admission-v1.md), [roadmap](ROADMAP.md) and [full new-chat prompt](CONTINUE_HERE.md). CI/merge awaits live checking.
- Next: compose this selector with actual audited warehouse ship assembly and the 14-phase economic turn, preserving separate PP and surface-material debits. Late PQ random and PPQ planet-share regular queues still missing.
- Evidence: `TESTED` conditional, not real accepted Host orders or `DIFF_VERIFIED` (#247 deferred).

## #265 — Classic terminal last-slot competing PBP owners (2026-10-22)

- Added `classic_terminal_pbp_last_slot.py`: one remaining Classic hard-cap ship ID, at least two eligible PBP owners (>=21), a UNIQUE top scorer and one queued base per eligible owner. Selection only under explicit `CALLER_ASSERTED_UNIQUE_HIGHEST_PBP_NO_CODES` hypothesis; modern NuHost PB-code/player-slot ranking is not independently settled.
- Executes winner's one ship with the existing strict BOM/warehouse auditor, debits only winner's mass-based PBP, preserves other owners' PBPs, unselected base warehouses and the saved standard pointer, while reconciling full 14-phase planetary economy before/after the hypothetical build.
- Added synthetic competitor reversal, cap20 hull PBP, after-economy tax financing, 30+ unsupported cases (ties, pb codes, cloning, extra slots, malformed rights, missing owner roster) and forged final-state/receipt tests.
- Updated [roadmap](ROADMAP.md), [detailed handoff](handoff/2026-10-22-classic-contested-final-pbp-slot-v1.md) and full [continuation prompt](CONTINUE_HERE.md). PR CI/merge not presumed until actual GitHub checks finish.
- Evidence: `TESTED conditional` ONLY; no real NuHost ranking, timing, accepted order, or `DIFF_VERIFIED` promotion. User-driven evidence remains parked in issue #247.
- Next: bounded late PQ/PPQ priority/regular allocation or bigger core Host composition with independently auditable resources.

## #264 — Classic consecutive PBP/pointer/warehouse carry (2026-10-22)

- Added `classic_bounded_multiturn_carry.py` with a typed complete inventory/owner/PBP/standard-pointer sidecar and complete explicit per-base orders for every modeled consecutive turn (up to eight).
- Each step dispatches either #263 priority+standard (one PBP-eligible owner) or #260 standard-only (none eligible) using the *carried* complete fleet, planet economy and warehouse stocks, with no external replenishment or PBP rewards; any failure in a later turn invalidates the **entire** sequence.
- Synthetic coverage: 8/12 ships, 21 PBP → priority ship ID9, standard ID10; next turn standard IDs11+12 with PBP20; third turn no ships under the cap. Also taxes after economy, stock depletion, missing idle warehouse, phantom catalog entry and broken second-turn blueprint.
- Updated [roadmap](ROADMAP.md), [technical handoff](handoff/2026-10-22-classic-multiturn-queue-carry-v1.md), and [next-chat prompt](CONTINUE_HERE.md). PR CI/merge success is not claimed until GitHub reports it.
- Still `TESTED` conditional, not independently authenticated queue/Host timing or `DIFF_VERIFIED`; work needing real participants remains [#247](https://github.com/Numillyash/planets-lab/issues/247).
- Next: implement a genuinely distinct bounded Classic contender or PQ/PPQ queue subcase (not more synthetic UI), then connect ordinary shipyard to wider Host.

## #263 — Classic shared priority + standard economic turn (2026-10-22)

- Added `classic_joint_priority_standard_turn.py` to join single uncontested Classic PBP priority (#261) to standard pointer (#259–260), reusing component/ship ledgers, a single shared finite hard-cap fleet and explicitly before/after 14-phase economy.
- Priority spends PBP but never advances standard pointer. After priority, a remaining 21+ PBP (another priority possible), multiple owner/candidate competition, mismatched base orders or missing independent inventory yield whole-turn ABSTAIN. Standard builds draw distinct free ship IDs in pointer order and preserve unselected warehouse stocks.
- Added synthetic two-owner/two-build and one-slot boundary, stocked priority source, tax-funded late builds, adversarial fabricated ship/planet receipts, and incomplete/contradictory queue tests. Evidence only `TESTED` conditional; no verified NuHost ordering or actual PBP receipts.
- Updated [roadmap](ROADMAP.md), detailed [technical handoff](handoff/2026-10-22-classic-joint-priority-standard-v1.md) and full [continuation prompt](CONTINUE_HERE.md). At PR preparation: CI/merge status pending live verification.
- Next: multi-turn carry/replay of pointer/PBP/warehouse sidecars and separate bounded contested/late queue models. Real accepted-Host evidence issue #247 remains deferred.

## #262 — Mandatory per-PR continuation and documentation (2026-10-22)

- **Scope:** introduce root `AGENTS.md`, PR checklist, canonical
  `docs/CONTINUE_HERE.md`, this changelog, explicit rules in
  `docs/WORKFLOW.md` / `README.md` / `docs/ROADMAP.md`,
  and mandatory PR CI diff validation in
  `tools/check_pr_handoff.py` + tests.
- **Problem solved:** chat context/branch resets no longer require users to
  manually forward a long conversation. The repo carries a complete current
  prompt; a PR cannot pass its new CI gate without refreshing that prompt,
  this PR log and one other meaningful project document.
- **Verification:** must be checked against the exact current PR head and
  follow-up merged main CI. PR CI will be validated for exact PR head; merge/main CI must be checked before any success claim.
- **Next:** Classic priority PBP (#261) composed with saved-pointer standard
  construction (#259–260), then late PQ/PPQ, then further Host integration.
- **Research limits:** user-dependent real-Host evidence remains parked in
  issue #247; local model code is `TESTED` at most, not new
  `DIFF_VERIFIED`.

## Earlier milestones (historical reference)

- **#259** — saved Classic ordinary build pointer and standard subphase
  ordering, conditional and fail-closed.
- **#260** — conditional standard pointer-selected assembly, lowest free ship
  IDs, per-base warehouse and full economy resource checks.
- **#261** — bounded single uncontested Classic priority build, 21-PBP
  threshold and mass-based cost, separate from ordinary subphase.
- **#253–258** — progressively compose orbital cargo, normal movement,
  planet economy, ordinary starbase facilities, ship component quote,
  warehouse assembly, and unthrottled multi-base shipbuilding.
- **#247 (issue)** — unresolved genuine accepted NuHost orders, independent
  Host timing, complete independent pre/post Host snapshots.
