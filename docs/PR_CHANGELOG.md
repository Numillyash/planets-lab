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
