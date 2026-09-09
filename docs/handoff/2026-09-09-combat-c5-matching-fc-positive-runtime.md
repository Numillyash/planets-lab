# C5 Host combat — matching Friendly Code positive runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains a separate special/campaign/Horwasp bucket.

## Runtime source

User runtime was executed on:

```text
ff66d4b8d268205adb8b0d096b12be4fee57df90
```

Artifact:

```text
artifacts/combat-c5-matching-fc-hwm-20260909-163418
```

Runtime status:

```text
targeted tests: PASS
audit rc:       0
payload conflicts: 0
```

The earlier collection failure on `67611a5...` was only a test import-path problem; it produced no mechanics evidence and was fixed by loading the diagnostic by file path.

## Positive factual VCR result

Across all 12 archives the audit found 55 factual ship-vs-ship VCR rows whose owner-current T-1 ship Friendly Codes matched exactly.

```text
matching_fc_vcr_rows = 55
```

Ordinary scope, excluding game `591478`:

```text
rows = 54
matching_fc_kind:
  documented_ship_exception = 54
hwm_observation:
  documented_ship_fc_exception = 54
matching_friendly_code:
  lfm = 32
  mkt = 22
hwm ordinary-exact-match candidates = 0
```

Special game `591478`:

```text
rows = 1
matching_fc_kind:
  documented_ship_exception = 1
matching_friendly_code:
  mkt = 1
```

No factual same-FC ship combat used an ordinary exact matching FC outside the documented MKT/NTP/LFM exceptions. No HWM candidate appeared:

```text
hwm_candidate_rows = 0
hwm_unshielded_first_site_rows = 0
```

No NTP example happened to occur in the current historical VCR population; this is absence of coverage, not evidence against the documented NTP exception.

## Interpretation

Primary Planets.nu documentation states that exact case-sensitive matching ship Friendly Codes normally suppress ship-vs-ship combat, with MKT/NTP/LFM as exceptions. The factual positive population is perfectly consistent with that boundary: all 55 observed same-FC combats are documented exceptions, and all 54 ordinary rows are MKT/LFM.

Evidence status after this gate:

```text
matching-FC suppression rule text:          DOCUMENTED
MKT/NTP/LFM exception rule text:            DOCUMENTED
matching-FC eligibility primitives:         TESTED
55 factual same-FC VCR rows:                CORPUS_OBSERVED
54/54 ordinary rows documented exceptions: CORPUS_OBSERVED
ordinary HWM factual support:               NOT PRESENT IN CURRENT CORPUS
ordinary exact-match suppression itself:    NOT YET DIFF_VERIFIED
```

The positive audit cannot prove suppression from absence. Do not promote `matching_ship_friendly_code_blocks_combat(...)` to historical `DIFF_VERIFIED` solely from this result.

## Immediate next gate — strict suppression controls

Build a negative-control population that establishes a pair would otherwise have been able to fight while avoiding the usual absence-of-VCR confounders.

Strong candidate shape:

1. both ships have unique owner-current records at T-1 and T;
2. different owners, unchanged across T-1 -> T;
3. both remain at the same exact coordinate across T-1 -> T, proving a stationary co-location through the combat phase;
4. exact ordinary matching FC, excluding MKT/NTP/LFM;
5. both hulls are known non-cloakable;
6. both have positive fuel before and after the Host turn;
7. both are armed / combat-capable;
8. at least one T-1 order requests combat through Kill! or Primary Enemy;
9. diplomacy relation signature is uniquely known and independently observed in factual ship combat, so Safe Passage is not silently blamed;
10. no factual VCR exists between the pair; a stricter subset also requires neither ship to participate in another ship VCR at that site.

If this population exists and is clean, it can supply the missing differential evidence for ordinary matching-FC suppression. If it is empty or diplomacy cannot be controlled, keep suppression DOCUMENTED + TESTED and move on rather than manufacturing certainty.
