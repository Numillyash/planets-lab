# C5 Host combat — matching Friendly Code suppression runtime — 2026-09-09

GitHub is the source of truth. PR #28 remains draft. Game `591478` remains excluded from ordinary tuning.

## Runtime source

User runtime was executed on:

```text
8bef008342c8760e6f33d450335f1b3fb95443bf
```

Artifact:

```text
artifacts/combat-c5-matching-fc-suppression-20260909-165947
```

Runtime status:

```text
targeted tests: PASS
audit rc:       0
payload conflicts: 0
```

## Strict suppression-control result

The audit deliberately searched only for negative controls where an ordinary exact matching Friendly Code was the remaining plausible blocker after controlling physical co-location, unchanged ownership, fuel, weapons, hostility, race/cloakability and directed diplomacy compatibility.

Observed pipeline:

```text
stationary_colocated_pairs       199341
different_owner_pairs             21307
ordinary_exact_matching_fc_pairs     11
hostile_order_pairs                    1
resolved_nonbird_pairs                 1
known_noncloaking_pairs                0
fueled_alive_armed_pairs               0
unique_relation_pairs                  0
directed_relation_combat_compatible_same_game_pairs 0
directed_relation_combat_compatible_same_turn_pairs 0
```

Final strict populations:

```text
strict_directed_relation_pair_vcr_absent_rows = 0
strict_isolated_no_ship_vcr_rows              = 0
same_turn_directed_relation_rows              = 0
same_turn_directed_relation_isolated_rows     = 0
```

## Interpretation

The strict population is empty for a concrete reason rather than an audit failure. Of eleven stationary different-owner pairs with ordinary exact matching FC, only one has Kill!/Primary-Enemy hostility. That one survives the resolved non-Bird filter but does not reach the known-noncloaking population. Therefore the corpus contains no clean independent pair on which absence of a VCR can be attributed uniquely to matching-FC suppression.

Do **not** relax the controls merely to manufacture a historical differential. In particular, a cloak-capable/unknown-cloakability row can be confounded by cloaking, Intercept/PIA and related pre-standard mechanics.

Evidence status after both matching-FC gates:

```text
matching-FC suppression text:                DOCUMENTED
MKT/NTP/LFM exception text:                  DOCUMENTED
matching-FC/HWM eligibility primitives:      TESTED
55 factual same-FC VCR rows:                 CORPUS_OBSERVED
54/54 ordinary factual rows MKT/LFM:         CORPUS_OBSERVED
ordinary HWM factual support:                NOT PRESENT IN CURRENT CORPUS
ordinary exact matching-FC suppression:      DOCUMENTED + TESTED
historical suppression differential:         NOT AVAILABLE IN CURRENT CORPUS
```

No NTP factual example exists in the present corpus; this remains only a coverage gap.

## Decision

Close this research gate without `DIFF_VERIFIED` promotion. The canonical tri-state matching-FC helper remains valid and fail-closed, and the positive MKT/LFM exception population is retained as corpus evidence.

Do not spend additional C5 time widening the negative-control population unless a future end-to-end Host differential contradicts the documented rule or new historical data supplies a clean pair.

## Immediate next work

Proceed to a unified dynamic ship pair-selection layer around the already bounded primitives:

1. normal Priority Intercept;
2. reciprocal Priority Intercept;
3. Bird Cloak-and-Intercept;
4. matching-FC eligibility/HWM override;
5. standard combat eligibility/order;
6. Intercept Interference and other unresolved dynamic suppressors must remain explicit fail-closed inputs rather than being guessed.

After pair selection is structurally integrated, continue with capture/reinsertion, the ship-to-planet repair boundary and planet/base participation.
