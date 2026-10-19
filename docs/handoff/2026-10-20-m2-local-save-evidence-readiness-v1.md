# M2 passive /game/save readiness: local-only evidence hygiene

Date: 2026-10-20. Baseline: validated `runtime-logs/m2-phase-identifiability-synthetic-v1/20261019T210532Z_608b76519061`, clean source `608b7651906185c981b907b7d559a98b7f586e68`, exit=0. The 96 fake experiments yielded 24 all-six-supported cases, all with **one** identical end state; 72 others had unsupported-model placements. The existing model experiment cannot independently identify NuHost order. Do **not** label conditional simulation, an abstention, or a client save request as `DIFF_VERIFIED`.

## Existing client evidence source

The repository already provides a passive, authorization-scoped `tools/client/planets_nu_save_payload_capture_v1.js` observer for browser-originated `/game/save` calls. It records up to 10 sanitized request/response observations plus counters for `/game/save` and `/game/turnready`. It creates no network requests itself, and its sanitation is limited to **known credential keys**. A response with HTTP 2xx and JSON `success: true` is a client-visible successful-shaped save response, **not independently confirmed server acceptance/execution of each order, not Host start, and not proof of a complete owner-order capture**. The turnready counter is not temporally linked to individual saved bodies.

## New strictly local readiness preflight

`src/planets_lab/sim/planetary_save_evidence_readiness.py` validates the exact known V1 report schema and bounds, uses fail-closed checks for unmasked known credential fields, and returns a *fixed allowlist* of integer counts and false provenance flags, **never a raw request, response body, player/game/ship ID, URL, field/path excerpt, fingerprint, client note or secret**. It classifies:
- retained save observations vs save calls not retained;
- syntactically parseable/nontruncated request bodies vs unavailable/omitted bodies (not claims of semantic order completeness);
- HTTP 2xx plus explicit JSON `success:true`, application `success:false`, HTTP errors, ambiguous/missing responses, and transport failures;
- observed known-key redaction markers;
- zero independent server-order receipt, external Host start witness, full pre/post state or NuHost execution verification.

The local CLI `tools/diagnostics/m2_local_save_readiness_v1.py` has two **exclusive** modes. A private source file must be outside the Git repo, regular, non-symlinked, owned by the invoking Unix UID, with mode 0600 and at most 32 MiB. Invalid or suspicious sources yield a generic ABSTAIN with no input path/error exposed. Input remains in memory, no file is created. `--synthetic` uses a fake browser report containing only invented values and may be sent to public `runtime-logs`. **Never pass `--private-input` through `run-with-runtime-evidence.sh`, and never commit or upload a browser report.** Sanitized client captures can still contain sensitive strategic text under unknown field names; never assume they are safe to share without review.

For GitHub source validation, the new tests check count partitions, all provenance flags, HTTP ambiguity, missing bodies, forged evidence status, known-key redaction failure, private file permission/symlink rejection and absence of injected source strings from stdout.

## Synthetic-only optional runtime gate

```bash
cd /root/projects/planets-lab
git pull --ff-only origin main
bash tools/run-m2-local-save-readiness-synthetic-v1-with-evidence.sh
```

Only the **synthetic** gate is published; it writes aggregate-only `gate.log` and `metadata.json` into a dated `runtime-logs/m2-local-save-readiness-synthetic-v1/`. Running this fake input establishes local software functionality only.

A real report, if the owner later opts in, is examined **only on their authorized local Unix machine**:
```bash
# Do not place the report or a private HMAC key anywhere under the git checkout
chmod 600 /absolute/private/location/save-report.json
python3 tools/diagnostics/m2_local_save_readiness_v1.py \
  --private-input /absolute/private/location/save-report.json
```

There is intentionally no network/upload behavior, browser auto-attachment or server acknowledgement invention. The user does not need to perform any live experiment for this PR. A genuine independent NuHost differential needs complete accepted order and state evidence plus a trustworthy time boundary; this software does **not** supply those missing records.

No original corpus read, `CURRENT` change, heldout32 entity sampling, C5/canonical combat or IntelBoard production change.
