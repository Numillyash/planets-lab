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
