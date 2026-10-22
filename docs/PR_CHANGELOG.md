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
