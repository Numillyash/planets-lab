## Purpose and implemented changes

<!-- What behavior/contract changed? Include supported and explicitly unsupported cases. -->

## Validation and provenance

<!-- Exact tests/CI, what was observed, what remains unverified. -->

## Required documentation and next-chat handoff

- [ ] Updated [docs/CONTINUE_HERE.md](../docs/CONTINUE_HERE.md) with a **complete, copy-ready** prompt for a new chat, referring to **this PR number** and the latest changes/remaining tasks.
- [ ] Added an entry for **this PR number** to [docs/PR_CHANGELOG.md](../docs/PR_CHANGELOG.md).
- [ ] Updated meaningful repository documentation (e.g. `docs/ROADMAP.md`, `README.md`, or a scoped `docs/handoff/*.md`) to match code, evidence and next steps.
- [ ] No Host/DIFF_VERIFIED claim is based only on local simulation, HMAC metadata, or client save success.
- [ ] No protected corpus/heldout32 or unrelated production subsystem changed.
- [ ] Checked PR CI for the latest exact HEAD and verified `main` after merge.

**Mandatory:** The CI handoff gate verifies all three documentation categories for **every PR**. A PR is not complete merely because tests pass. This template is a human-readable reminder; enforcement is in `tools/check_pr_handoff.py`.
